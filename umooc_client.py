"""
A client that simulates the desktop device to communicate with umooc server
"""

import requests
import time
import re
from bs4 import BeautifulSoup
import os.path


def get_img(img_id):
    #  TODO:save images to a specific path
    if not os.path.isfile(f'{img_id}.jpg'):
        resp = requests.get(f'http://eol.ctbu.edu.cn/meol/common/ckeditor/openfile.jsp?id={img_id}',
                            headers={'User-Agent': 'yomooc'},
                            stream=True)
        with open(f'{img_id}.jpg', 'wb') as img_file:
            for chunk in resp:
                img_file.write(chunk)


class LoginError(BaseException):
    def __init__(self, error_info):
        super().__init__(self)
        self.error_info = error_info

    def __str__(self):
        return self.error_info


class ParseError(BaseException):
    def __init__(self, error_info):
        super().__init__(self)
        self.error_info = error_info

    def __str__(self):
        return self.error_info


class TopicListPage(object):
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

            thread_title = title_dom.string
            if title_dom.name == 'b':
                thread_id = title_dom.parent.attrs['href'].split('=')[1]
            elif title_dom.name == 'a':
                thread_id = title_dom.attrs['href'].split('=')[1]
            else:
                raise ParseError('Cannot get thread id')

            self.topics.append({'title': thread_title,
                                'id': thread_id})


class TopicPage(object):
    def __init__(self, raw_doc):
        self.raw_html = raw_doc
        self.replies = []
        self.parse()

    def parse(self):
        page_soup = BeautifulSoup(self.raw_html, 'html.parser')
        inputs = page_soup.find_all('input')
        for reply_input in inputs:
            contents = []
            for content in BeautifulSoup(reply_input.attrs['value'].replace('&#55357;', '[emoji]'),
                                         'html.parser').contents:
                if content.name != 'br':
                    if content.name == 'div':
                        for div_child in content.contents:
                            if div_child.name == 'img':
                                img_id = div_child['src'][38:-2]
                                get_img(img_id)
                                contents.append({'type': 'img', 'img_id': img_id})
                    else:  # pure text
                        contents.append({'type': 'text', 'content': content})
            self.replies.append(
                {'username': reply_input.find_parents('tr')[0].h6.contents[0][25:],  # remove the redundant spaces
                 'time': reply_input.find_parents('tr')[0].find_all('li')[1].span.string[7:],
                 'content': contents})  # umooc just does not support emoji


class UmoocClient(object):
    def __init__(self):
        self.js_session_id = ''
        self.dwr_session_id = ''
        self.topic_list = []
        self.replies = {}

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

    def get_topic_list(self, page=1):
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

        # it is needed to request some pages before getting the topic list
        # maybe the server is judging which course the user is
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
        topic_list_page = TopicListPage(resp.text)
        self.topic_list = topic_list_page.topics
        return self.topic_list

    def get_replies(self, thread_ids=None):
        if thread_ids is None:
            thread_ids = [topic['id'] for topic in self.topic_list]
        for thread_id in thread_ids:
            resp = requests.get(f'http://eol.ctbu.edu.cn/meol/common/faq/thread.jsp?threadid={thread_id}',
                                headers={'User-Agent': 'yomooc'})
            topic_page = TopicPage(resp.text)
            self.replies[thread_id] = topic_page.replies
        return self.replies
