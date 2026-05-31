# 批量跑步重构说明

## 变更概述

新增多人配置 + 并行执行能力，原始 `main.py` 未改动。

## 新增文件

| 文件 | 说明 |
|------|------|
| `run.py` | 新入口，支持 `-f` 指定多人配置、`-a` 自动模式、`--parallel` 并行执行 |
| `tools/batch_run.py` | 核心模块：`YunConfig`（配置类）+ `YunRunner`（执行器），无全局变量 |
| `configs/multi.ini` | 多人配置模板，`[DEFAULT]` 放公共配置，`[person:xxx]` 放个人信息 |

## 用法

```bash
# 串行执行（一个人跑完跑下一个）
python run.py -f configs/multi.ini -a

# 并行执行（所有人同时跑）
python run.py -f configs/multi.ini -a --parallel

# 只跑指定的人
python run.py -f configs/multi.ini -a --parallel -p 张三,李四

# 限制并发数
python run.py -f configs/multi.ini -a --parallel --workers 2

# 指定任务文件夹、不加漂移
python run.py -f configs/multi.ini -a --task-folder ./tasks_else --no-drift
```

## 配置格式

```ini
[DEFAULT]
# 公共配置，所有 [person:xxx] 自动继承
school_host = https://sports.aiyyd.com:8000
cipherkey = ...
# 跑步参数
min_distance = 2.5
split_count = 10
# ...

[person:张三]
token =
device_id = 1091764153471218
uuid = 1091764153471218
device_name = OnePlus(PKG110)
sys_edition = 16
username =
password =

[person:李四]
token =
device_id = 8234567890123456
uuid = 8234567890123456
device_name = Xiaomi(2304FPN6DC)
sys_edition = 14
username =
password =
```

每人只需填写差异项，公共配置从 `[DEFAULT]` 继承。

## 与原方案（EasyAutoRunServer/run.sh）的对比

| 维度 | run.sh 多进程方案 | run.py 多线程方案 |
|------|-------------------|-------------------|
| 配置 | 每人一份完整 config 副本 | `[DEFAULT]` 共享 + 个人覆盖 |
| 并行 | nohup 多进程 | ThreadPoolExecutor 多线程 |
| 状态 | 翻日志文件 | 实时打印 + 汇总 |
| 错误 | 一人崩不影响其他，但无汇总 | 异常隔离 + 结果统计 |
| 并发控制 | 无，全部一起起 | `--workers` 控制 |

## 与原 main.py 的关系

`batch_run.py` **不依赖** `main.py`，是从中提取逻辑重写的：

- `set_args()` + 全局变量 → `YunConfig` 类
- `default_post()` → `YunRunner._default_post()`（读 `self.cfg` 而非全局变量）
- `Yun_For_New` 打表逻辑 → `YunRunner.run_auto()`
- `Login.main()` 交互式登录 → `YunRunner._login()`（纯接口，不读文件不 input）

原 `main.py` 完全未改，原有单人用法不受影响。

## 依赖

与原项目一致：

```
requests
gmssl
tqdm
pycryptodome
```
