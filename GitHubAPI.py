#!/usr/bin/env python
# coding=utf-8
# python version 3.7
# 使用github api 监控 关键字 动态


import os, sys
import requests, json, sqlite3
import time, datetime, threading
from email.header import Header
from email.mime.text import MIMEText
import smtplib
import configparser, argparse

"""
#自动下载 https://codeload.github.com/nytimes/covid-19-data/zip/master
#监控和邮件分离
#记录上一次脚本启动、数据库更新
"""


class Githublook():
    def __init__(self, qkey=[]):
        self._session = requests.session()
        self._qkeys = qkey  # 多个要监控的关键字
        self._get_sleep = 7  # 未经身份验证的请求，速率限制使您每分钟最多可以进行10个请求
        self._createds = []  # 新建项目列表
        self._updateds = []  # 更新项目列表
        # self._lock = threading.Lock()
        # ======================================以下是可修改的参数=======================================
        self._db_name = 'github.db'  # 数据库文件名
        # self._mail_sleep = 6 * 60 * 60  # 每六小时发送一次统计报告
        self._look_sleep = 10 * 60  # 每10分钟监控一次GitHub
        self._to_reciver = ['test2@qq.com', 'test2@qq.com']  # 收件人列表
        self._mail_host = "smtp.163.com"  # 邮件服务器
        self._mail_user = "test1@163.com"  # 用户名
        self._mail_pass = "******"  # 密码/授权码 (部分邮箱需要开启第三方smtp服务，使用授权码登陆)

    # 数据库创建\校验
    def sqlite3_create(self):  # 创建数据库、表
        conn = sqlite3.connect(self._db_name)
        conn.execute("""CREATE TABLE IF NOT EXISTS github(
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        node_id TEXT,full_name TEXT, html_url TEXT, 
        description TEXT,created_at TEXT,updated_at TEXT,
        stargazers_count TEXT,language TEXT,keyword TEXT,);""")  # 如果表不存在就创建

        conn.close()

    # 数据库插入\更新
    def sqlite3_do(self, insert_=[]):  # 插入到数据库
        new_ = []
        up_ = []
        conn = sqlite3.connect(self._db_name)
        cur = conn.cursor()  # 创建事物'游标'
        for i in insert_:
            v = (i['node_id'], i['full_name'], i['html_url'], i['description'], i['created_at'], i['updated_at'],
                 i['stargazers_count'], i['language'])
            _nodeid = list(cur.execute("SELECT updated_at FROM github WHERE node_id='%s'" % (i['node_id'])))
            if len(_nodeid) > 0:  # 判断是否存在
                old_updated_at = list(_nodeid[0])[0]
                if i['updated_at'] == old_updated_at:
                    continue
                else:  # 已存在且时间有变化则更新
                    qy = "UPDATE github SET node_id=?,full_name=?,html_url=?,description=?,created_at=?,updated_at=?,stargazers_count=?,language=? WHERE node_id='%s';" % (
                        i['node_id'])
                    up_.append(i['node_id'])
            else:  # 未存在则添加
                qy = "INSERT INTO github(node_id,full_name,html_url,description,created_at,updated_at,stargazers_count,language)VALUES(?,?,?,?,?,?,?,?);"
                new_.append(i['node_id'])
            cur.execute(qy, v)
        conn.commit()  # 提交当前事物?
        conn.close()
        return new_, up_  # 返回添加和更新的列表

    # 从数据库取出信息构造邮件body
    def sqlit3_to_mailtext(self, new_=[], up_=[]):
        text_ = u'新添%d;更新%d\n' % (len(new_), len(up_))
        conn = sqlite3.connect(self._db_name)
        cur = conn.cursor()
        qy = "SELECT full_name,html_url,updated_at,language,description FROM github WHERE node_id='%s'"
        text_ += '%s新添记录%d个%s\n' % ('=' * 10, len(new_), '=' * 10)
        for n in new_:
            _data = cur.execute(qy % n)
            text_ += str(list(_data)) + '\n'
        text_ += '%s更新记录%d个%s\n' % ('=' * 10, len(up_), '=' * 10)
        for n in up_:
            _data = cur.execute(qy % n)
            text_ += str(list(_data)) + '\n'
        conn.close()
        return text_

    # 发送监控报告到指定邮箱
    def send_text_mail(self):
        print(u'新添%d;更新%d' % (len(self._createds), len(self._updateds)))
        if len(self._createds) == 0:  # and len(self._updateds) == 0
            return  # 如果无任何信息就不发邮件了
        mailtext = self.sqlit3_to_mailtext(self._createds, self._updateds)
        message = MIMEText(mailtext, 'plain', 'utf-8')  # 构造邮件内容 #文本内容，文本格式（plain:正文），编码
        message['Subject'] = Header('Github监控报告', 'utf-8')  # 邮件标题
        message['From'] = self._mail_user
        message['To'] = ";".join(self._to_reciver)
        message['Cc'] = self._mail_user  # 抄送给自己,防止被当作垃圾邮件拒绝发送
        try:
            # smtpObj = smtplib.SMTP_SSL(self._mail_host, 465)  # ssl连接
            smtpObj = smtplib.SMTP(self._mail_host, 25)
            smtpObj.login(self._mail_user, self._mail_pass)
            smtpObj.sendmail(self._mail_user, self._to_reciver, message.as_string())
            smtpObj.quit()
            print(u"邮件发送成功")
        except smtplib.SMTPException as e:
            print(u"Error: 邮件发送失败,转存到本地.Case:%s" % e)
            _time = time.localtime(time.time())
            filename = str('%d-%d-%d_%d-%d-%d' % (
                _time.tm_year, _time.tm_mon, _time.tm_mday, _time.tm_hour, _time.tm_min, _time.tm_sec))
            with open(filename + '.txt', 'w') as f:
                f.write(mailtext)
        # 无论是否发送成功，都清空列表
        self._createds.clear()  # 清空监控列表
        self._updateds.clear()

    # 验证身份,更改监控参数（偶尔出现登陆失败，需要新运行脚本）
    def github_auth(self, username=None, password=None, token=None):
        # session = requests.session()
        api_root_url = "https://api.github.com"
        if username and password:
            self._session.auth = (username, password)
        elif token:
            self._session.headers["Authorization"] = "token {}".format(token)
        else:
            print(u'github_auth:不支持的验证方式')
        _test = self._session.get(api_root_url, verify=False)
        if _test.status_code == 200:
            print(u'登陆成功 %d %s' % (_test.status_code, _test.text))
            self._get_sleep = 2  # 对于使用基本身份验证，OAuth或客户端ID和密码的请求，您每分钟最多可以进行30个请求。
        else:
            print(u'登陆错误 %d %s' % (_test.status_code, _test.text))
        # return session

    # 获取关键字从开始日期到结束日期的数据
    def github_date2sqlite3(self, s='2015-01-01', e=None):
        self.sqlite3_create()
        if e is None:  # 默认结束日期为当前日期
            _time = time.localtime(time.time())
            e = str(_time.tm_year) + '-' + str(_time.tm_mon) + '-' + str(_time.tm_mday)
        date_list = []  # 保存日期的列表
        date = datetime.datetime.strptime(s, '%Y-%m-%d')
        end = datetime.datetime.strptime(e, '%Y-%m-%d')
        while date <= end:
            date_list.append(date.strftime('%Y-%m-%d'))
            date = date + datetime.timedelta(1)
        print(u'预计需要%.2f分钟' % (len(date_list) * self._get_sleep / 60))
        # 按日期开始访问api获取数据
        github_search_appi = 'https://api.github.com/search/repositories?q=%s+created:%s'
        for d in date_list:
            for k in self._qkeys:
                time.sleep(self._get_sleep)
                # self.get_github_control(k + '+created:' + d)
                insert_ = self.get_github_page(github_search_appi % (k, d))  # 一般来说指定当天的不会超过100条
                _list1, _list2 = _g.sqlite3_do(insert_)
                print(u'同步完成%s %s 有%d个项目' % (d, k, len(insert_)))

    # 统计总数,设置分页
    def get_github_control(self, qkey):
        github_search_appi = 'https://api.github.com/search/repositories?q='
        gurl = github_search_appi + '%s&sort=updated&order=desc&page=1&per_page=1' % qkey
        _gjson = self._session.get(gurl, verify=False).json()
        github_total_count = int(_gjson['total_count'])  # 统计结果总数，分页提取
        conn = sqlite3.connect(self._db_name)
        sql_total_count = list(conn.execute('SELECT COUNT(id) FROM github;'))  # 获取数据库记录数
        conn.close()
        print(u'当前Github项目总数%d;数据库记录%d' % (github_total_count, list(sql_total_count[0])[0]))
        self._createds.clear()  # 清空监控列表
        self._updateds.clear()
        # for i in range(1, int(total_count / 100) + 1):#通过api最多获取1000个结果
        #     time.sleep(self._get_sleep)
        #     print(u'正在处理第%d页' % i)
        gurl = github_search_appi + '%s&sort=updated&order=desc&page=%d&per_page=100' % (
            qkey, 1)  # 搜索存储库每页最多返回100个结果
        insert_ = self.get_github_page(gurl)
        _list1, _list2 = _g.sqlite3_do(insert_)
        self._createds += _list1
        self._updateds += _list2
        # return insert_

    # 从api返回的json中提取指定元素
    def get_github_page(self, gurl):
        _gjson = self._session.get(gurl, verify=False).json()  # 获取返回的json字符串
        # with open('repositories.json', 'r+', encoding='utf-8') as f:
        #     _gjson = json.load(f)
        infos_ = []  # 提取json信息
        _items = _gjson['items']
        for g in _items:
            tmps_ = {}
            # 取出需要的参数值，重新构造字典
            tmps_['node_id'] = g['node_id']
            tmps_['full_name'] = g['full_name']
            tmps_['html_url'] = g['html_url']
            tmps_['description'] = g['description']
            tmps_['created_at'] = g['created_at']
            tmps_['updated_at'] = g['updated_at']
            tmps_['stargazers_count'] = g['stargazers_count']
            tmps_['language'] = g['language']
            infos_.append(tmps_)
        return infos_

    def run(self):
        self.sqlite3_create()
        _n = 0
        while 1: #为解决cmd输出卡住，不在死循环
            _n += 1
            _time = time.localtime(time.time())
            print('%d-%02d-%02d_%02d:%02d:%02d 第%d次监控' % (
                _time.tm_year, _time.tm_mon, _time.tm_mday, _time.tm_hour, _time.tm_min, _time.tm_sec, _n))
            try:
                for k in self._qkeys:
                    _t1 = threading.Thread(target=Githublook.get_github_control, args=(self, k))
                    _t1.start()
                    _t1.join()
                    if len(self._qkeys) > 1:
                        time.sleep(self._get_sleep * 2)  # get_github_control会访问2次GitHubAPI
                _t2 = threading.Thread(target=Githublook.send_text_mail, args=(self,))
                _t2.start()
                _t2.join()
                # self.get_github_control('cve-20')
                # self.send_text_mail()
            except:
                print('第%d次监控出错' % _n)
            time.sleep(self._look_sleep)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=u'使用github api 监控关键字动态')
    parser.add_argument('-u', type=str, help=u'指定用户名', nargs=1)
    parser.add_argument('-p', type=str, help=u'指定密码', nargs=1)
    parser.add_argument('-t', type=str, help=u'指定Github账号生成的token值', nargs=1)
    parser.add_argument('-d', type=str, help=u'获取从指定日期(2015-01-01)到当前日期的项目信息', nargs=1)
    args = parser.parse_args()

    requests.packages.urllib3.disable_warnings()  # 关闭警告
    _g = Githublook(['cve-20', ])  # 多个关键字监控
    if args.u and args.p:
        _g.github_auth(username=args.u, password=args.p)
    elif args.t:
        _g.github_auth(token=args.t)  # token=''
    if args.d:
        _g.github_date2sqlite3(args.d[0], None)  # 默认结束日期为当前日期
    else:
        _g.run()
