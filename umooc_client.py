"""
A client that simulates the desktop device to communicate with umooc server
"""

import requests
import time
import re
from bs4 import BeautifulSoup


class LoginError(BaseException):
    def __init__(self, ErrorInfo):
        super().__init__(self)
        self.errorinfo = ErrorInfo

    def __str__(self):
        return self.errorinfo


class TopicPage(object):
    def __init__(self, raw_doc):
        self.raw_html = raw_doc
        self.topics = []
        self.parse()

    def parse(self):
        page_soup = BeautifulSoup(self.raw_html, 'html.parser')
        topic_table = page_soup.find_all('table')[1]
        for tr in topic_table.findChildren('tr')[1:]:
            title_dom = tr.findChildren('td')[1].findChild('b')
            if title_dom is None:
                title_dom = tr.findChildren('td')[1].findChild('a')
                title_dom.string = title_dom.string[:-9]  # remove the redundant '\n        '

            self.topics.append(
                {'title': title_dom.string})


class UmoocClient(object):
    def __init__(self):
        self.js_session_id = ''
        self.dwr_session_id = ''

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
                             allow_redirects=False)
        if resp.status_code == 302:
            self.js_session_id = resp.cookies['JSESSIONID']
        else:
            raise LoginError('Fail to get session')

    def get_topics(self, page):
        # get dwr session id
        resp = requests.post('http://eol.ctbu.edu.cn/meol/dwr/call/plaincall/__System.generateId.dwr',
                             headers={'Origin': 'http://eol.ctbu.edu.cn',
                                      'Content-Type': 'text/plain',
                                      'User-Agent': 'yomooc',
                                      'Referer': 'http://eol.ctbu.edu.cn/meol/jpk/course/layout/newpage/index.jsp'
                                                 '?courseId=46445',
                                      'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7',
                                      'Cookie': f'JSESSIONID={self.js_session_id}'},
                             data=f'callCount=1\n'
                                  f'c0-scriptName=__System\n'
                                  f'c0-methodName=generateId\n'
                                  f'c0-id=0\n'
                                  f'batchId=0\n'
                                  f'instanceId=0\n'
                                  f'page=%2Fmeol%2Fjpk%2Fcourse%2Flayout%2Fnewpage%2Findex.jsp%3FcourseId%3D46445\n'
                                  f'scriptSessionId=\n'
                                  f'windowName=\n')
        self.dwr_session_id = re.search(r'[^"]*"\);', resp.text).group()[:-3]

        # get topics

        # it is needed to request some pages before getting the topic list, maybe the server is judging which course the
        # user is
        requests.get('http://eol.ctbu.edu.cn/meol/jpk/course/layout/newpage/index.jsp?courseId=46445',
                     headers={'Upgrade-Insecure-Requests': '1',
                              'User-Agent': 'yomooc',
                              'Cookie': f'JSESSIONID={self.js_session_id}; '
                                        f'DWRSESSIONID={self.dwr_session_id}'})
        requests.get('http://eol.ctbu.edu.cn/meol/jpk/course/layout/newpage/default_demonstrate.jsp'
                     '?courseId=46445',
                     headers={'Upgrade-Insecure-Requests': '1',
                              'User-Agent': 'yomooc',
                              'Referer': 'http://eol.ctbu.edu.cn/meol/jpk/course/layout/newpage/index.jsp'
                                         '?courseId=46445',
                              'Cookie': f'JSESSIONID={self.js_session_id}; '
                                        f'DWRSESSIONID={self.dwr_session_id}'})
        resp = requests.get(f'http://eol.ctbu.edu.cn/meol/common/faq/forum.jsp'
                            f'?viewtype=thread'
                            f'&forumid=102211'
                            f'&cateId=0'
                            f'&s_gotopage={page}',
                            headers={'Upgrade-Insecure-Requests': '1',
                                     'User-Agent': 'yomooc',
                                     'Referer': 'http://eol.ctbu.edu.cn/meol/common/faq/forum.jsp'
                                                '?count=MODITIME'
                                                '&forumid=102211',
                                     'Cookie': f'JSESSIONID={self.js_session_id}; '
                                               f'DWRSESSIONID={self.dwr_session_id}'})
        topic_page = TopicPage(resp.text)
        topic_page.parse()
        return topic_page.topics
