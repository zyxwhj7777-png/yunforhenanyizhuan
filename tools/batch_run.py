"""
云运动批量跑步模块
支持多人配置 + 并行执行
"""
import base64
import math
import random
import time
import requests
import json
import configparser
import hashlib
import os
import gzip
import traceback
from typing import List, Dict, Optional
from base64 import b64encode, b64decode
from gmssl.sm4 import CryptSM4, SM4_ENCRYPT, SM4_DECRYPT
import gmssl.sm2 as sm2
from tqdm import tqdm

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from tools.drift import add_drift
# Login 已内联到 YunRunner._login()，不再直接 import


class YunConfig:
    """单人配置，无全局变量"""

    def __init__(self, conf: configparser.ConfigParser, section: str):
        # 学校/密钥
        self.school_host = conf.get(section, "school_host")
        self.cipher_key = conf.get(section, "cipherkey")
        self.cipher_key_encrypted = conf.get(section, "cipherkeyencrypted")
        self.app_edition = conf.get(section, "app_edition")
        self.public_key = b64decode(conf.get(section, "PublicKey"))
        self.private_key = b64decode(conf.get(section, "PrivateKey"))
        self.md5key = conf.get(section, "md5key")
        self.platform = conf.get(section, "platform")
        self.school_id = conf.get(section, "school_id", fallback="")
        self.school_login_url = conf.get(section, "school_login_url", fallback="appLogin")
        # 用户
        self.token = conf.get(section, "token")
        self.device_id = conf.get(section, "device_id")
        self.map_key = conf.get(section, "map_key")
        self.device_name = conf.get(section, "device_name")
        self.sys_edition = conf.get(section, "sys_edition")
        self.utc = conf.get(section, "utc") or str(int(time.time()))
        self.uuid = conf.get(section, "uuid")
        self.sign = conf.get(section, "sign")

        # 跑步参数
        self.min_distance = float(conf.get(section, "min_distance"))
        self.allow_overflow_distance = float(conf.get(section, "allow_overflow_distance"))
        self.single_mileage_min_offset = float(conf.get(section, "single_mileage_min_offset"))
        self.single_mileage_max_offset = float(conf.get(section, "single_mileage_max_offset"))
        self.cadence_min_offset = int(conf.get(section, "cadence_min_offset"))
        self.cadence_max_offset = int(conf.get(section, "cadence_max_offset"))
        self.split_count = int(conf.get(section, "split_count"))
        self.exclude_points = json.loads(conf.get(section, "exclude_points"))
        self.min_consume = float(conf.get(section, "min_consume"))
        self.max_consume = float(conf.get(section, "max_consume"))
        self.strides = float(conf.get(section, "strides"))
        self.auto_task_folder = conf.get(section, "auto_task_folder")

        # 登录
        self.login_username = conf.get(section, "username", fallback="")
        self.login_password = conf.get(section, "password", fallback="")

        # 名称标识（section名）
        self.name = section

    def get_sign(self, utc, uuid):
        sb = f"platform={self.platform}&utc={utc}&uuid={uuid}&appsecret={self.md5key}"
        return hashlib.md5(sb.encode("utf-8")).hexdigest()


class YunRunner:
    """单人跑步执行器，所有状态都是实例变量，可并行"""

    def __init__(self, config: YunConfig):
        self.cfg = config
        self._init_crypto()
        self._ensure_token()

    def _init_crypto(self):
        """初始化 SM2/SM4 加密"""
        pub_hex = self._bytes_to_hex(self.cfg.public_key[1:])
        pri_hex = self._bytes_to_hex(self.cfg.private_key)
        self._sm2 = sm2.CryptSM2(public_key=pub_hex, private_key=pri_hex, mode=1, asn1=True)

    @staticmethod
    def _bytes_to_hex(b: bytes) -> str:
        return hex(int.from_bytes(b, 'big'))[2:].upper()

    def _encrypt_sm4(self, value, is_bytes=False):
        crypt = CryptSM4()
        crypt.set_key(b64decode(self.cfg.cipher_key), SM4_ENCRYPT)
        raw = value if is_bytes else value.encode("utf-8")
        return b64encode(crypt.crypt_ecb(raw)).decode()

    def _decrypt_sm4(self, value):
        crypt = CryptSM4()
        crypt.set_key(b64decode(self.cfg.cipher_key), SM4_DECRYPT)
        return crypt.crypt_ecb(b64decode(value))

    def _ensure_token(self):
        """确保有可用 token，无则自动登录"""
        if self.cfg.token:
            return
        print(f"[{self.cfg.name}] token为空，尝试自动登录...")
        try:
            result = self._login()
            if result is None:
                raise RuntimeError("登录失败")
            self.cfg.token, self.cfg.device_id, self.cfg.device_name, self.cfg.uuid, self.cfg.sys_edition = result
            print(f"[{self.cfg.name}] 登录成功")
        except Exception as e:
            raise RuntimeError(f"[{self.cfg.name}] 登录失败: {e}")

    def _login(self):
        """基于 YunConfig 直接登录，不依赖外部 config.ini / input()"""
        from tools.getUrl_Id import md5_encryption, encrypt_sm4 as url_encrypt_sm4

        utc = int(time.time())
        cfg = self.cfg

        if not cfg.login_username or not cfg.login_password:
            raise RuntimeError(f"[{cfg.name}] 缺少 username/password 且无 token，无法登录")

        device_id = cfg.device_id or str(random.randint(1000000000000000, 9999999999999999))
        uuid = cfg.uuid or device_id
        device_name = cfg.device_name or "Xiaomi"
        sys_edition = cfg.sys_edition or "14"
        login_url = cfg.school_host + "/login/" + cfg.school_login_url

        encrypt_data = json.dumps({
            "password": cfg.login_password,
            "schoolId": cfg.school_id or "161",
            "userName": cfg.login_username,
            "type": "1"
        })
        sign_data = f"platform=android&utc={utc}&uuid={uuid}&appsecret={cfg.md5key}"
        sign = md5_encryption(sign_data)
        content = url_encrypt_sm4(encrypt_data, b64decode(cfg.cipher_key), isBytes=False)

        headers = {
            "token": "", "isApp": "app", "deviceId": uuid, "deviceName": device_name,
            "version": cfg.app_edition, "platform": "android", "uuid": uuid,
            "utc": str(utc), "sign": sign,
            "Content-Type": "application/json; charset=utf-8",
            "Accept-Encoding": "gzip", "User-Agent": "okhttp/3.12.0"
        }
        data = {"cipherKey": cfg.cipher_key_encrypted, "content": content}
        response = requests.post(login_url, headers=headers, json=data)
        result_text = response.text

        if "{" in result_text:
            dec = response.json()
        else:
            dec = json.loads(self._decrypt_sm4(result_text).decode())

        if "500" in str(dec):
            raise RuntimeError(dec.get("msg", "登录返回500"))

        token = dec['data']['token']
        print(f"[{cfg.name}] 登录成功, token={token[:20]}...")
        return token, device_id, device_name, uuid, sys_edition

    def _default_post(self, router, data, is_bytes=False):
        url = self.cfg.school_host + router
        utc = str(int(time.time()))
        sign = self.cfg.get_sign(utc, self.cfg.uuid)
        headers = {
            'token': self.cfg.token,
            'isApp': 'app',
            'deviceId': self.cfg.device_id,
            'deviceName': self.cfg.device_name,
            'version': self.cfg.app_edition,
            'platform': 'android',
            'Content-Type': 'application/json; charset=utf-8',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip',
            'User-Agent': 'okhttp/3.12.0',
            'utc': utc,
            'uuid': self.cfg.uuid,
            'sign': sign
        }
        payload = {
            "cipherKey": self.cfg.cipher_key_encrypted,
            "content": self._encrypt_sm4(data, is_bytes=is_bytes)
        }
        resp = requests.post(url=url, data=json.dumps(payload), headers=headers)
        try:
            return self._decrypt_sm4(resp.text).decode()
        except Exception:
            return resp.text

    def run_auto(self, task_folder: Optional[str] = None, drift: bool = True):
        """自动跑步：打表模式 + 漂移"""
        folder = task_folder or self.cfg.auto_task_folder
        print(f"[{self.cfg.name}] === 开始自动跑步 ===")
        print(f"[{self.cfg.name}] 任务文件夹: {folder} | 漂移: {'是' if drift else '否'}")

        # 获取首页信息
        home = json.loads(self._default_post("/run/getHomeRunInfo", ""))['data']['cralist'][0]
        ra_type = home['raType']
        ra_id = home['id']
        school_id = home['schoolId']
        ra_run_area = home['raRunArea']
        ra_cadence_min = home['raCadenceMin'] + self.cfg.cadence_min_offset
        ra_cadence_max = home['raCadenceMax'] + self.cfg.cadence_max_offset

        # 随机选一个 task 文件
        files = sorted(os.listdir(folder))
        chosen = os.path.join(folder, random.choice(files))
        print(f"[{self.cfg.name}] 选择任务: {chosen}")

        with open(chosen, 'r', encoding='utf-8') as f:
            task_map = json.loads(f.read())

        if drift:
            task_map = add_drift(task_map)

        # start
        start_data = {'raRunArea': ra_run_area, 'raType': ra_type, 'raId': ra_id}
        start_resp = json.loads(self._default_post('/run/start', json.dumps(start_data)))
        if start_resp['code'] != 200:
            print(f"[{self.cfg.name}] 启动失败: {start_resp}")
            return False

        record_start_time = start_resp['data']['recordStartTime']
        run_record_id = start_resp['data']['id']
        user_name = start_resp['data']['studentId']
        print(f"[{self.cfg.name}] 任务创建成功，开始跑步...")

        # 发送 split points
        points_list = task_map['data']['pointsList']
        duration = task_map['data']['duration']
        split_count = self.cfg.split_count
        batch = []
        count = 0

        for point in tqdm(points_list, desc=f"[{self.cfg.name}]", leave=True):
            p = {
                'point': point['point'],
                'runStatus': '1',
                'speed': point['speed'],
                'isFence': 'Y',
                'isMock': False,
                "runMileage": point['runMileage'],
                "runTime": point['runTime'],
                "ts": str(int(time.time()))
            }
            batch.append(p)
            count += 1
            if count == split_count:
                self._send_split(batch, task_map, ra_cadence_min, ra_cadence_max, school_id, run_record_id, user_name)
                sleep_time = duration / len(points_list) * split_count
                time.sleep(sleep_time)
                count = 0
                batch = []

        if batch:
            self._send_split(batch, task_map, ra_cadence_min, ra_cadence_max, school_id, run_record_id, user_name)

        # finish
        print(f"[{self.cfg.name}] 发送结束信号...")
        finish_data = {
            'recordMileage': task_map['data']['recordMileage'],
            'recodeCadence': task_map['data']['recodeCadence'],
            'recodePace': task_map['data']['recodePace'],
            'deviceName': self.cfg.device_name,
            'sysEdition': self.cfg.sys_edition,
            'appEdition': self.cfg.app_edition,
            'raIsStartPoint': 'Y',
            'raIsEndPoint': 'Y',
            'raRunArea': ra_run_area,
            'recodeDislikes': str(task_map['data']['recodeDislikes']),
            'raId': str(ra_id),
            'raType': ra_type,
            'id': str(run_record_id),
            'duration': task_map['data']['duration'],
            'recordStartTime': record_start_time,
            'manageList': task_map['data']['manageList'],
            'remake': '1'
        }
        resp = self._default_post("/run/finish", json.dumps(finish_data))
        print(f"[{self.cfg.name}] 完成! {resp}")
        return True

    def _send_split(self, points, task_map, cadence_min, cadence_max, school_id, run_record_id, user_name):
        data = {
            "StepNumber": int(float(points[-1]['runMileage']) - float(points[0]['runMileage'])) / self.cfg.strides,
            'a': 0, 'b': None, 'c': None,
            "mileage": float(points[-1]['runMileage']) - float(points[0]['runMileage']),
            "orientationNum": 0,
            "runSteps": random.uniform(cadence_min, cadence_max),
            'cardPointList': points,
            "simulateNum": 0,
            "time": float(points[-1]['runTime']) - float(points[0]['runTime']),
            'crsRunRecordId': run_record_id,
            "speeds": task_map['data']['recodePace'],
            'schoolId': school_id,
            "strides": self.cfg.strides,
            'userName': user_name
        }
        resp = self._default_post(
            "/run/splitPointCheating",
            gzip.compress(data=json.dumps(data).encode("utf-8")),
            is_bytes=True
        )
        print(f'  [{self.cfg.name}] split: {resp}')


def load_configs(conf_path: str) -> List[YunConfig]:
    """
    从 INI 文件加载多人配置。
    格式：每个 [person:xxx] 节是一个人，可继承 [DEFAULT] 中的公共值。
    """
    conf = configparser.ConfigParser()
    conf.read(conf_path, encoding="utf-8")

    configs = []
    for section in conf.sections():
        if section.startswith("person:") or section.startswith("Person:"):
            try:
                cfg = YunConfig(conf, section)
                configs.append(cfg)
            except Exception as e:
                print(f"[警告] 加载配置 {section} 失败: {e}")
    return configs
