#coding=utf-8
from selenium import webdriver
import selenium
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from bs4 import BeautifulSoup
import requests
import logging
import re
import time
import mysql_insert
import urllib3
#from urllib.parse import quote
import random
import json
import sys
import cgi
sys.setdefaultencoding('utf8')
import HTMLParser
import settings

BASE_URL = 'http://weixin.sogou.com'

UA = u"Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"

def get_html(url):
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    print( dcap)
    dcap["phantomjs.page.settings.userAgent"] = (
        UA
    )
    dcap["takesScreenshot"] = (False)
    #t0 = time.time()
    try:
        driver = webdriver.PhantomJS(desired_capabilities=dcap, service_args=['--load-images=no'])
        driver.set_page_load_timeout(240)
        driver.command_executor._commands['executePhantomScript'] = ('POST', '/session/$sessionId/phantom/execute')

        driver.execute('executePhantomScript', {'script': '''
            var page = this; // won't work otherwise
            page.onResourceRequested = function(requestData, request) {
                if ((/http:\/\/.+?\.css/gi).test(requestData['url']) || requestData['Content-Type'] == 'text/css') {
                    console.log('The url of the request is matching. Aborting: ' + requestData['url']);
                    request.abort();
                }
            }
            ''', 'args': []})
    except selenium.common.exceptions.WebDriverException:
        return None
    try:
        driver.get(url)
        html = driver.page_source
    except Exception as e:
        html = None
        logging.error(e)
    finally:
        driver.quit()
    return html

def get_html_direct(url,cookies=None):
    if not cookies:
        cookies = update_cookies()
    headers = {"User-Agent": UA}
    r = requests.get(url, headers=headers, cookies=cookies, timeout=20)
    return r.text

def get_account_info(open_id=None, link=None, cookies=None):
    url = None
    if open_id:
        url = BASE_URL + '/gzh?openid=' + open_id
    if link:
        url = link
    #html = get_html(url)
    html = get_html_direct(url, cookies=cookies)
    #print(html)
    if not html:
        return None
    soup = BeautifulSoup(html)
    info_box = soup.select('#weixinname')[0].parent
    account_info = {}
    account_info['account'] = info_box.select('h4 span')[0].text.split('：')[1].strip()
    account_info['name'] = info_box.select('#weixinname')[0].text
    account_info['address'] = url
    account_info['description'] = info_box.select('.sp-txt')[0].text
    img_list = soup.select('.pos-box img')
    account_info['logo'] = soup.select(".img-box img")[0]['src']
    account_info['qr_code'] = img_list[1]['src']
    return account_info


def parse_list(open_id=None, link=None,cookie=None):
    if open_id:
        url = BASE_URL + '/gzh?openid=' + open_id
    elif link:
        url = link
    else:
        return None
    html = get_html_direct(url,cookie)
#    html = get_html(url)
    if not html:
        return None
    soup = BeautifulSoup(html)
    #ls = soup.select('#wxbox .txt-box')
    ls = soup.select('script')
    link_list = []
    for item in ls:
        matchObj = re.search(r'.*\n.*msgList = (.*)\n.*seajs\.use.*',item.text,re.M|re.I)
        if matchObj:
            msg = matchObj.group(1).strip()
            msg = msg[:-1]
            article_info = json.loads(msg)
            for v in article_info['list']:
                item_dict = {}
                item_dict['source_url'] = 'https://mp.weixin.qq.com'+v['app_msg_ext_info']['content_url']
                item_dict['title']      = v['app_msg_ext_info']['title']
                item_dict['sub_title']  = v['app_msg_ext_info']['digest']
                item_dict['author']     = v['app_msg_ext_info']['author']
                item_dict['cover']      = v['app_msg_ext_info']['cover']

#        item_dict['title'] = item.a.text
#        item_dict['link'] = item.a['href']
                link_list.append(item_dict['source_url'])
    return link_list


def parse_essay(link):
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    try:
        r = s.get(link)
        html = r.text
        soup = BeautifulSoup(html)
        print soup
        essay   = {}
        img_arr = []
        p = re.compile(r'\?wx_fmt.+?\"')
        content = str(soup.select("#js_content")[0]).replace('data-src', 'src')
        essay['content']        = re.sub(p, '"', content)
        essay['writer']         = soup.select('#post-user')[0].text
        essay['publish_time']   = soup.select('#post-date')[0].text
        essay['source_url']     = link
        essay['source_domain']  = u'mp.weixin.qq.com'
        essay['title']          = soup.select('.rich_media_title')[0].text.strip()
        essay['source_keywords']= u''
        essay['source_pos']     = u''
        essay['origin']         = u'微信公众号'
        essay['summary']        = u''

        img_ = soup.find_all(name='img',class_='') 
        print img_
        lenth = len(img_)
        for i in range(lenth):
            if img_[i].attrs['data-src']:
                img_url = img_[i].attrs['data-src']
            else:
                continue
            img_arr.append(img_url)
        if img_arr:
            print json.dumps(img_arr)
            essay['source_pics']    = json.dumps(img_arr)
            source_pics, ymt_pics = common.upload_img(img_arr,'https://mmbiz.qpic.cn')
        else:
            essay['source_pics']= u''
        essay['ymt_pics']       = ymt_pics ? json.dumps(ymt_pics) : ''
        essay['pic_count']      = len(img_arr)
    except Exception:
        return essay

    return essay


def weixin_search(name, cookies=None):
    url = BASE_URL + '/weixin?type=1&s_from=input&ie=utf8&_sug_=n&_sug_type_=&query=' + name
    #html = get_html(url)
    html = get_html_direct(url, cookies=cookies)
#    print(html)
    soup = BeautifulSoup(html)
#    print(soup)
    ls = soup.select(".tit")
    print(ls)
    search_list = []
    for item in ls:
        account_info = {}
#        account_info['account'] = item.select('h4 span')[0].text.split('：')[1].strip()
        account_info['name'] = item.select('a')[0].text
        account_info['address'] = item.select('a')[0]['href']
#        print(item.select('a')[0].text)
#        account_info['open_id'] = item['href'].split('openid=')[1]
#        account_info['description'] = item.select('.sp-txt')[0].text
#        account_info['logo'] = item.select('.img-box img')[0]['src']
        try:
            pass
#            account_info['latest_title'] = item.select('.sp-txt a')[0].text
#            account_info['latest_link'] = item.select('.sp-txt a')[0]['href']
        except IndexError:
            pass
#        print account_info['name'],name
        if account_info['name'] == name:
            search_list.append(account_info)
    print(account_info)
    return search_list

def update_cookies():
    s = requests.Session()
    headers = {"User-Agent": UA}
    s.headers.update(headers)
    url = BASE_URL + '/weixin?query=123'
    r = s.get(url)
    if 'SNUID' not in s.cookies:
        p = re.compile(r'(?<=SNUID=)\w+')
        s.cookies['SNUID'] = p.findall(r.text)[0]
        suv = ''.join([str(int(time.time()*1000000) + random.randint(0, 1000))])
        s.cookies['SUV'] = suv
    return s.cookies


def run_spider():
    html_parser = HTMLParser.HTMLParser()
    cookies = update_cookies()
    for account in settings.account_name:
        account_info  = weixin_search(account['name'])
        url_list = []
        for link in account_info:
            l = link['address']
            parse_res = parse_list(None,l,cookies)
            if parse_res:
                url_list.extend(parse_res)
        if url_list:
            for li in url_list:
                print  html_parser.unescape(li)
                dynamic = parse_essay(html_parser.unescape(li))
                print dynamic
                msq = mysql_insert.Mysql_insert()
                res = msq.process_item(dynamic)
                time.sleep(1)

if __name__ == '__main__':
    run_spider()
#    html_parser = HTMLParser.HTMLParser()
#    open_id = 'oIWsFt3nvJ2jaaxm9UOB_LUos02k'
#    print(account_info)
#    cookies = update_cookies()
#    t0 = time.time()
#    print(get_account_info(open_id,cookies=cookies))
    #print(weixin_search("简书",cookies))
#    account_info = weixin_search(u'农资与市场杂志')
#    print url_list
#    t2 = time.time()
#    print(parse_essay('http://mp.weixin.qq.com/s?__biz=MjM5NjM4OTAyMA==&mid=205212599&idx=4&sn=6a1de7a7532ba0bcbc633c253b61916f&3rd=MzA3MDU4NTYzMw==&scene=6#rd'))
#    t3 = time.time()
#    print t1-t0, t2-t1, t3-t2
