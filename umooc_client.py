"""
A client that simulates the desktop device to communicate with umooc server
"""

import requests
import time


class LoginError(BaseException):
    def __init__(self, ErrorInfo):
        super().__init__(self)
        self.errorinfo = ErrorInfo

    def __str__(self):
        return self.errorinfo


class UmoocClient(object):
    def __init__(self):
        self.session = ''

    def login(self, username, password):
        resp = requests.post('http://eol.ctbu.edu.cn/meol/loginCheck.do',
                             headers={'Cache-Control': 'max-age=0',
                                      'Upgrade-Insecure-Requests': '1',
                                      'Origin': 'http://eol.ctbu.edu.cn',
                                      'Content-Type': 'application/x-www-form-urlencoded',
                                      'User-Agent': 'yomooc',
                                      'Referer': 'http://eol.ctbu.edu.cn/meol/common/security/login.jsp?enterLid=46445',
                                      'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7'
                                      },
                             data=f'logintoken={str(time.time()).replace(".", "")[:-4]}'
                                  f'&enterLid=46445'
                                  f'&IPT_LOGINUSERNAME={username}'
                                  f'&IPT_LOGINPASSWORD={password}',
                             allow_redirects=False,
                             proxies={'http': 'http://127.0.0.1:54385'})
        if resp.status_code == 302:
            self.session = resp.cookies['JSESSIONID']
        else:
            raise LoginError('Fail to get session')
