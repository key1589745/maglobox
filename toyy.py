#!/usr/bin/env python

# -*- encoding: utf-8 -*-

'''

@Desc    :toy

'''
import os
import requests
from bs4 import BeautifulSoup
import json
import time
import muggle_ocr

import urllib3
import SSL


class CustomHttpAdapter (requests.adapters.HTTPAdapter):
    # "Transport adapter" that allows us to use custom ssl_context.

    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = urllib3.poolmanager.PoolManager(
            num_pools=connections, maxsize=maxsize,
            block=block, ssl_context=self.ssl_context)


def get_legacy_session():
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
    session = requests.session()
    session.mount('https://', CustomHttpAdapter(ctx))
    return session


url_login = "https://uis.fudan.edu.cn/authserver/login"
url_dailyFudan = "https://zlapp.fudan.edu.cn/site/ncov/fudanDaily"
url_get_info = 'https://zlapp.fudan.edu.cn/ncov/wap/fudan/get-info'
url_png = 'https://zlapp.fudan.edu.cn/backend/default/code'
url_save = 'https://zlapp.fudan.edu.cn/ncov/wap/fudan/save'
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 " \
     "Safari/537.36 "


class Login_Fudan:

    def __init__(self, username, pwd):
        self.username = username
        self.pwd = pwd
        self.header = {'User-Agent': UA}
        self.data = {'username': self.username,
                     'password': self.pwd
                     }
        self.session = get_legacy_session()

    def logIn(self):
        '''
        登陆复旦uis系统
        :return:
        '''
        response = self.session.get(url_login)
        soup = BeautifulSoup(response.text, 'lxml')

        # 筛选出所有post请求体需要的参数（token）
        def has_name_and_value(tag):
            return tag.has_attr('name') and tag.has_attr('value') and 'username' not in tag['name'] and 'password' not \
                   in tag['name']

        for item in soup.body.form.find_all(has_name_and_value):
            self.data.update(zip([item['name']], [item['value']]))
        # 登陆账号
        self.session.post(url_login, data=self.data)

    def check(self):
        '''
        判断今日是否已经提交平安复旦
        :return:
        '''
        # 获取上次提交的信息并用json接收，转为字典处理
        self.last_info = json.loads(self.session.get(url_get_info).text)
        self.cur_info = self.last_info['d']['info']
        today = time.strftime('%Y%m%d')
        if self.cur_info['date'] == today:
            print("今日已提交")
            return True
        else:
            print("今日未提交")
            return False

    def checkin(self):
        '''
        提交平安复旦
        :return:
        '''
        old_info = self.last_info['d']['oldInfo']
        area = old_info['area']
        province = old_info['province']
        city = old_info['city']
        sfzx = old_info['sfzx']
        self.cur_info.update(
            {
                'area': area,
                'province': province,
                'city': city,
                'sfzx': sfzx,
                'ismoved': '0'
            }
        )
        response = self.session.get(url_png)
        sdk = muggle_ocr.SDK(model_type=muggle_ocr.ModelType.Captcha)
        code = sdk.predict(image_bytes=response.content)
        self.cur_info['code'] = code
        self.session.post(url_save, data=self.cur_info)
        print('正在提交平安复旦')


if __name__ == '__main__':
    username = os.getenv("USERNAME")
    pwd = os.getenv("PASSWORD")
    login = Login_Fudan(username, pwd)
    login.logIn()
    num = 10
    while not login.check() and num > 0:
        login.checkin()
        time.sleep(30)
        num -= 1
    if not login.check():
        raise Exception("still failing after 10 times!!!")
