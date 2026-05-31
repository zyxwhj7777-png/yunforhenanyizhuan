import random
import time
from base64 import b64decode
import requests
import json
import configparser
from getUrl_Id import getschool_Url_Id, encrypt_sm4 ,decrypt_sm4, md5_encryption

SM4_BLOCK_SIZE = 16
conf = configparser.ConfigParser()

class Login():

    def main():

        utc = int(time.time())

        #读取ini
        conf.read('./config.ini', encoding='utf-8')

        #判断[Login]是否存在
        if 'Login' not in conf.sections():
            conf.add_section('Login')
            conf.set('Login', 'username', '')
            conf.set('Login', 'password', '')
            with open('./config.ini', 'w', encoding='utf-8') as f:
                conf.write(f)

        #判断school_id是否在[Yun]中
        if 'school_id' not in conf['Yun']:
            conf.set('Yun', 'school_id', '100')
            with open('./config.ini', 'w', encoding='utf-8') as f:
                conf.write(f)

        #读取ini配置
        username = conf.get('Login', 'username') or input('未找到用户名，请输入用户名：')
        password = conf.get('Login', 'password') or input('未找到密码，请输入密码：')
        iniDeviceId = conf.get('User', 'device_id')
        iniDeviceName = conf.get('User', 'device_name')
        iniuuid = conf.get('User', 'uuid')
        iniSysedition = conf.get('User', 'sys_edition')
        appedition = conf.get('Yun', 'app_edition')
        platform = conf.get('Yun', 'platform')
        schoolName = conf.get('Yun','school_name') or input("未找到学校名称，请输入学校名称：")
        conf.set('Yun','school_Name',schoolName)
        url, scId = getschool_Url_Id(schoolName)
        if url and scId:
            conf.set('Yun', 'school_host', url)
            conf.set('Yun', 'school_id', str(scId))
            with open('./config.ini', 'w', encoding='utf-8') as f:
                conf.write(f)
        schoolid = conf.get('Yun', 'school_id')
        schoolHost = conf.get('Yun', 'school_host')

        # if schoolHost == 'http://210.45.246.53:8080':
        #     url = schoolHost + '/login/appLoginHGD'
        # else:
        #     url = schoolHost + '/login/appLogin'
        # 不同学校不同，例如 appLoginHGD appLoginCHZU appLogin
        school_login_url = conf.get('Yun',"school_login_url")
        url = schoolHost + '/login/' + school_login_url

        if username != conf.get('Login', 'username'):
            conf.set('Login', 'username', username)
            with open('./config.ini', 'w', encoding='utf-8') as f:
                conf.write(f)
        if password != conf.get('Login', 'password'):
            conf.set('Login', 'password', password)
            with open('./config.ini', 'w', encoding='utf-8') as f:
                conf.write(f)
        #如果部分配置为空则随机生成
        if iniDeviceId != '':
            DeviceId = iniDeviceId
        else:
            DeviceId = str(random.randint(1000000000000000, 9999999999999999))
            conf.set('User', 'device_id', DeviceId)
            with open('./config.ini', 'w', encoding='utf-8') as f:
                conf.write(f)
        if iniuuid != '':
            uuid = iniuuid
        else:
            uuid = DeviceId

        if iniDeviceName != '':
            DeviceName = iniDeviceName
        else:
            print('DeviceName为空 请输入希望使用的设备名\n留空则使用默认名')
            DeviceName = input() or 'Xiaomi'

        if iniSysedition != '':
            sys_edition = iniSysedition
        else:
            print('Sys_edition为空 请输入希望使用的设备名\n留空则使用14')
            sys_edition = input() or '14'


        #md5签名结果用hex
        encryptData = '''{"password":"'''+password+'''","schoolId":"'''+schoolid+'''","userName":"'''+username+'''","type":"1"}'''
        #签名结果
        md5key = conf.get('Yun', 'md5key')
        sign_data='platform=android&utc={}&uuid={}&appsecret={}'.format(utc,uuid,md5key)
        sign=md5_encryption(sign_data)
        default_key = conf.get('Yun', 'cipherkey')
        CipherKeyEncrypted = conf.get('Yun', 'cipherKeyEncrypted')
        content = encrypt_sm4(encryptData, b64decode(default_key),isBytes=False)
        # content=content[:-24]
        headers = {
            "token": "",
            "isApp": "app",
            "deviceId": uuid,
            "deviceName": DeviceName,
            "version": appedition,
            "platform": platform,
            "uuid": uuid,
            "utc": str(utc),
            "sign": sign,
            "Content-Type": "application/json; charset=utf-8",
            "Accept-Encoding": "gzip",
            "User-Agent": "okhttp/3.12.0"
        }
        # 请求体内容
        data = {
            "cipherKey": CipherKeyEncrypted,
            "content": content
        }
        # 发送POST请求
        response = requests.post(url, headers=headers, json=data)
        # 打印响应内容
        result=response.text

        if "{" in result : # 有的学校会直接返回未加密内容 如果是JSON（用最粗暴的方式判断）
            DecryptedData = response.json()
        else :
            DecryptedData = json.loads(decrypt_sm4(result, b64decode(default_key)).decode())
        # 判断是否返回错误信息并停止
        if "500" in str(DecryptedData) :
            print(DecryptedData["msg"])
            exit()

        token=DecryptedData['data']['token']

        if response.status_code == 200: # 成功登录时 返回信息
            print("登录成功，本次登录尝试获得的token为：" + token + "  本次生成的uuid为：" + uuid)
            print("!请注意! 使用脚本登录后会导致手机客户端登录失效\n请尽量减少手机登录次数，避免被识别为多设备登录代跑")
            return token,DeviceId,DeviceName,uuid,sys_edition
        # 如果不是200响应，先打印响应再退出 便于排查问题
        print(result)
        exit()