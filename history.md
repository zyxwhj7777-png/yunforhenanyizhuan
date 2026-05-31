### 获取历史记录的api

都3周了，PR估计是等不来了，这个api我就自己实现了。
别再提垃圾issue了，这功能我帮你封装了还不行吗...


```python
from main import *
set_args("./cfg_my.ini")
from main import * # 重新加载配置，防止bug，实话说不推荐这种方式，直接import main比较好

hl = default_post("/run/listXnYearXqByStudentId", data='')
print(hl) # 列表输出：
```
```json
{
    "msg": "操作成功",
    "code": 200,
    "data": [
        {
            "xq": "2",
            "sjd": "2024.02.01-2025.07.01",
            "value": "crs_run_record100",
            "key": "2024-2025 学年 第二学期",
            "xnYear": "2024-2025"
        },
        {
            "xq": "1",
            "sjd": "2024.09.01-2025.01.31",
            "value": "crs_run_record100_20241",
            "key": "2024-2025 学年 第一学期",
            "xnYear": "2024-2025"
        },
        {
            "xq": "1",
            "sjd": "2023.09.01-2024.01.31",
            "value": "crs_run_record100_20231",
            "key": "2023-2024 学年 第一学期",
            "xnYear": "2023-2024"
        },
        {
            "xq": "2",
            "sjd": "2024.02.01-2024.07.01",
            "value": "crs_run_record100_20232",
            "key": "2023-2024 学年 第二学期",
            "xnYear": "2023-2024"
        },
        {
            "xq": "1",
            "sjd": "2022.09.01-2023.01.31",
            "value": "crs_run_record100_20221",
            "key": "2022-2023 学年 第一学期",
            "xnYear": "2022-2023"
        },
        {
            "xq": "2",
            "sjd": "2023.02.01-2023.07.01",
            "value": "crs_run_record100_20222",
            "key": "2022-2023 学年 第二学期",
            "xnYear": "2022-2023"
        },
        {
            "xq": "1",
            "sjd": "2021.09.01-2022.01.31",
            "value": "crs_run_record100_20211",
            "key": "2021-2022 学年 第一学期",
            "xnYear": "2021-2022"
        },
        {
            "xq": "2",
            "sjd": "2022.02.01-2022.07.01",
            "value": "crs_run_record100_20212",
            "key": "2021-2022 学年 第二学期",
            "xnYear": "2021-2022"
        },
        {
            "xq": "1",
            "sjd": "2020.09.01-2021.01.31",
            "value": "crs_run_record100_20201",
            "key": "2020-2021 学年 第一学期",
            "xnYear": "2020-2021"
        },
        {
            "xq": "2",
            "sjd": "2021.02.01-2021.07.01",
            "value": "crs_run_record100_20202",
            "key": "2020-2021 学年 第二学期",
            "xnYear": "2020-2021"
        }
    ]
}
```
```python
his_list = default_post("/run/crsReocordInfoList", data=json.dumps({"tableName":'crs_run_record100'}))
print(his_list) # 获取list，如下
```
```json
{
    "msg": "操作成功",
    "code": 200,
    "data": {
        "isLiveStatus": "N",
        "sumKm": 2.24,
        "isMorning": "N",
        "sumNumber": "1",
        "rank": [
            {
                "year": "2025",
                "month": "02",
                "monthKm": 2.24,
                "rankList": [
                    {
                        "endTime": "25日 12:04 ",
                        "id": "1894234322682114049",
                        "recordEndTime": "2025-02-25 12:04:56",
                        "recordMileage": 2.24,
                        "recodePace": 0.0,
                        "recodeCadence": 0,
                        "recodeDislikes": 0,
                        "isQualified": "1",
                        "duration": 0,
                        "raName": "",
                        "pointsList": [],
                        "runYear": "2025",
                        "runMonth": "02",
                        "runYearMonth": "2025-02",
                        "manageList": [],
                        "pointsArrayList": []
                    }
                ]
            }
        ],
        "morningNum": 0
    }
}
```
```python
b64decode(default_key)
his = default_post("/run/crsReocordInfo", data=json.dumps({"id":'1894234322682114049', "tableName":'crs_run_record100'}))
text = gzip.decompress(decrypt_sm4(his, b64decode(default_key))).decode()
print(text)

# 最后得到历史记录，这里pointList省略1k个点，只是展示格式
```
```json
{
    "msg": "操作成功",
    "code": 200,
    "data": {
        "id": "1894234322682114049",
        "studentId": "xxx",
        "raId": 47,
        "raType": "T3",
        "deviceName": "xxx",
        "sysEdition": "12",
        "appEdition": "3.4.7",
        "recordStartTime": "2025-02-25 11:53:50",
        "recordEndTime": "2025-02-25 12:04:56",
        "recordMileage": 2.24,
        "recodePace": 4.73,
        "recodeCadence": 275,
        "recodeDislikes": 3,
        "recordRunningPath": "G:/pointspoints\\20250225\\8a16389835f94f789288eb082d580585.zip",
        "isQualified": "1",
        "remake": "1",
        "appealStatus": "R5",
        "duration": 636,
        "managePoints": "117.20665,31.773417|Y|0=117.206288,31.774426|N|1=117.205987,31.773925|Y|2=117.206662,31.774406|Y|1=117.206316,31.773431|N|4=",
        "isMorning": "R0",
        "pointsList": [ 
            {
                "id": 0,
                "point": "117.20580164336735,31.774133782169393",
                "speed": 4.0,
                "runStatus": 1,
                "runRecordId": 0,
                "runTime": "632",
                "isFence": "Y",
                "runMileage": "2221.892578125",
                "ts": "1740456284"
            },
            {
                "id": 0,
                "point": "117.20579591638486,31.77407385056626",
                "speed": 2.51,
                "runStatus": 1,
                "runRecordId": 0,
                "runTime": "633",
                "isFence": "Y",
                "runMileage": "2228.57861328125",
                "ts": "1740456284"
            },
            {
                "id": 0,
                "point": "117.20576977803755,31.774012831368182",
                "speed": 3.47,
                "runStatus": 1,
                "runRecordId": 0,
                "runTime": "634",
                "isFence": "Y",
                "runMileage": "2235.799560546875",
                "ts": "1740456294"
            },
            {
                "id": 0,
                "point": "117.20573674150782,31.773976629211404",
                "speed": 5.21,
                "runStatus": 1,
                "runRecordId": 0,
                "runTime": "635",
                "isFence": "Y",
                "runMileage": "2240.894287109375",
                "ts": "1740456294"
            }
        ],
        "schoolId": 100,
        "manageList": [
            {
                "point": "117.20665,31.773417",
                "marked": "Y",
                "index": 0
            },
            {
                "point": "117.206288,31.774426",
                "marked": "N",
                "index": 1
            },
            {
                "point": "117.205987,31.773925",
                "marked": "Y",
                "index": 2
            },
            {
                "point": "117.206662,31.774406",
                "marked": "Y",
                "index": 1
            },
            {
                "point": "117.206316,31.773431",
                "marked": "N",
                "index": 4
            }
        ],
        "className": "计算机xxx",
        "studentName": "xxx",
        "sex": "1",
        "pointsArrayList": []
    }
}
```