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


def parse_args():
    parser = argparse.ArgumentParser(description='云运动批量跑步脚本')
    parser.add_argument('-f', '--config', type=str, default='./configs/multi.ini',
                        help='多人配置文件路径 (默认: configs/multi.ini)')
    parser.add_argument('-m', '--auto', action='store_false',default=True,
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
    """单人执行入口"""
    name = config.name
    try:
        runner = YunRunner(config)
        if args.auto:
            ok = runner.run_auto(
                task_folder=args.task_folder or None,
                drift=not args.no_drift
            )
        else:
            print(f"[{name}] 非自动模式暂不支持批量，请使用 -a 参数")
            ok = False
        return name, ok, None
    except Exception as e:
        return name, False, str(e)


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
                name, ok, err = future.result()
                results.append((name, ok, err))
                if err:
                    print(f"\n[{name}] ❌ 失败: {err}")
                else:
                    print(f"\n[{name}] {'✅ 成功' if ok else '⚠️ 未完成'}")
    else:
        # 串行执行
        results = []
        for cfg in configs:
            name, ok, err = run_single(cfg, args)
            results.append((name, ok, err))
            if err:
                print(f"\n[{name}] ❌ 失败: {err}")
            else:
                print(f"\n[{name}] {'✅ 成功' if ok else '⚠️ 未完成'}")

    # 汇总
    elapsed = time.time() - start
    print(f"\n{'='*50}")
    print(f"  执行完毕 | 耗时: {elapsed:.1f}s")
    success = sum(1 for _, ok, _ in results if ok)
    fail = len(results) - success
    print(f"  成功: {success} | 失败: {fail}")
    if fail:
        for name, _, err in results:
            if err:
                print(f"    ❌ {name}: {err}")
    print(f"{'='*50}")


if __name__ == '__main__':
    main()
