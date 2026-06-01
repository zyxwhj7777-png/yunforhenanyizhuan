#!/usr/bin/env python3
"""
  python run.py                                # 默认并行自动跑
  python run.py -f configs/multi.ini           # 指定配置文件，并行自动跑
  python run.py -f configs/multi.ini -p 张三,李四  # 只跑指定的人
  python run.py --serial                       # 串行执行
  python run.py --no-drift                     # 不添加漂移
"""
import argparse
import sys
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from tools.batch_run import load_configs, YunRunner

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')


def parse_args():
    parser = argparse.ArgumentParser(description='云运动批量跑步脚本')
    parser.add_argument('-f', '--config', type=str, default='./configs/multi.ini',
                        help='多人配置文件路径 (默认: configs/multi.ini)')
    parser.add_argument('-m', '--auto', action='store_false', default=True,
                        help='手动跑步模式（默认自动模式，打表+漂移，无需交互）')
    parser.add_argument('-p', '--persons', type=str, default='',
                        help='只跑指定的人，逗号分隔 (如: 张三,李四)')
    parser.add_argument('--serial', action='store_true',
                        help='串行执行（依次执行）')
    parser.add_argument('--workers', type=int, default=0,
                        help='并行线程数 (默认=人数)')
    parser.add_argument('--task-folder', type=str, default='',
                        help='覆盖配置中的 auto_task_folder')
    parser.add_argument('--no-drift', action='store_true',
                        help='不添加漂移')
    return parser.parse_args()


def run_single(config, args):
    """单人执行入口，返回 (name, detail_dict|None, error_str|None)"""
    name = config.name
    try:
        runner = YunRunner(config)
        if args.auto:
            result = runner.run_auto(
                task_folder=args.task_folder or None,
                drift=not args.no_drift
            )
        else:
            print(f"[{name}] 非自动模式暂不支持批量，请使用 -a 参数")
            return name, None, "非自动模式暂不支持"

        if result is False:
            return name, None, "启动失败（返回False）"

        # result 是 dict（成功）或 True（兼容旧逻辑）
        if isinstance(result, dict):
            return name, result, None
        return name, {}, None

    except Exception as e:
        return name, None, str(e)


def write_log(results, elapsed, configs, args):
    """写入日志文件 logs/YYYY-MM-DD.log"""
    os.makedirs(LOG_DIR, exist_ok=True)
    now = datetime.now()
    log_path = os.path.join(LOG_DIR, now.strftime('%Y-%m-%d') + '.log')

    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"运行时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"配置文件: {args.config}")
    lines.append(f"执行模式: {'并行' if not args.serial else '串行'}")
    lines.append(f"漂移: {'否' if args.no_drift else '是'}")
    lines.append(f"人员: {', '.join(c.name for c in configs)}")
    lines.append(f"耗时: {elapsed:.1f}s")
    lines.append(f"{'='*60}")

    for name, detail, err in results:
        lines.append('')
        lines.append(f'--- {name} ---')
        if err:
            lines.append(f'  状态: ❌ 失败')
            lines.append(f'  原因: {err}')
        elif detail:
            lines.append(f'  状态: ✅ 成功')
            lines.append(f'  里程: {detail.get("mileage", "N/A")} km')
            lines.append(f'  时长: {detail.get("duration", "N/A")} s')
            lines.append(f'  配速: {detail.get("pace", "N/A")}')
            lines.append(f'  任务文件: {detail.get("task_file", "N/A")}')
            lines.append(f'  漂移: {detail.get("drift", "N/A")}')
            lines.append(f'  记录ID: {detail.get("run_record_id", "N/A")}')
        else:
            lines.append(f'  状态: ⚠️ 未完成（无详情）')

    lines.append('')
    lines.append(f"{'='*60}")
    lines.append('')

    with open(log_path, 'a', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"\n📝 日志已写入: {log_path}")


def main():
    args = parse_args()

    # 加载配置
    configs = load_configs(args.config)
    if not configs:
        print(f"错误: 配置文件 {args.config} 中未找到 [person:xxx] 节")
        sys.exit(1)

    # 过滤指定人员
    if args.persons:
        selected = set(args.persons.split(','))
        configs = [c for c in configs if c.name in selected]
        if not configs:
            print(f"错误: 配置中未找到指定人员: {args.persons}")
            sys.exit(1)

    print(f"{'='*50}")
    now = datetime.now()
    print(now.strftime("%Y-%m-%d %H:%M:%S"))
    print(f"  云运动批量跑步")
    print(f"  配置文件: {args.config}")
    print(f"  人员数量: {len(configs)}")
    print(f"  人员列表: {', '.join(c.name for c in configs)}")
    print(f"  执行模式: {'并行' if not args.serial else '串行'}")
    print(f"  自动模式: {'是' if args.auto else '否'}")
    print(f"{'='*50}\n")

    start = time.time()

    if not args.serial:
        # 并行执行
        max_workers = args.workers if args.workers > 0 else len(configs)
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(run_single, cfg, args): cfg.name for cfg in configs}
            for future in as_completed(futures):
                name, detail, err = future.result()
                results.append((name, detail, err))
                if err:
                    print(f"\n[{name}] ❌ 失败: {err}")
                else:
                    mileage = detail.get('mileage', '?') if detail else '?'
                    print(f"\n[{name}] ✅ 成功 | 里程: {mileage} km")
    else:
        # 串行执行
        results = []
        for cfg in configs:
            name, detail, err = run_single(cfg, args)
            results.append((name, detail, err))
            if err:
                print(f"\n[{name}] ❌ 失败: {err}")
            else:
                mileage = detail.get('mileage', '?') if detail else '?'
                print(f"\n[{name}] ✅ 成功 | 里程: {mileage} km")

    # 汇总
    elapsed = time.time() - start
    print(f"\n{'='*50}")
    print(f"  执行完毕 | 耗时: {elapsed:.1f}s")
    success = sum(1 for _, d, e in results if e is None)
    fail = len(results) - success
    print(f"  成功: {success} | 失败: {fail}")
    if fail:
        for name, _, err in results:
            if err:
                print(f"    ❌ {name}: {err}")
    print(f"{'='*50}")

    # 写日志
    write_log(results, elapsed, configs, args)


if __name__ == '__main__':
    main()
