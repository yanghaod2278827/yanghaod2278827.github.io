#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓豆瓣「看过」列表的最近若干条 + 总数，写成 data/douban.json 供站点渲染。

Cookie 不进仓库（本仓库是公开的）：
    1) 环境变量 DOUBAN_COOKIE，或
    2) 用户目录下的 ~/douban_cookie.txt（一行，形如 dbcl2="xxxx:yyyy"; ck=AbCd）

豆瓣 ID 用 --user 指定，默认 d2278827。

用法：
    python3 scripts/fetch_douban.py [--pages 4] [--user d2278827]
抓取失败时保留上一份 JSON 并退出码 1（与 fetch_data.py 同口径）。
"""
import argparse
import json
import os
import random
import re
import ssl
import sys
import time
import urllib.request

if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'douban.json')

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def load_cookie():
    c = os.environ.get('DOUBAN_COOKIE', '').strip()
    if c:
        return c
    for p in (os.path.expanduser('~/douban_cookie.txt'), os.path.expanduser('~/.douban_cookie')):
        if os.path.exists(p):
            with open(p, encoding='utf-8') as f:
                c = f.read().strip()
            if c:
                return c
    raise SystemExit('missing cookie: set DOUBAN_COOKIE or create ~/douban_cookie.txt '
                     '(F12 -> Application -> Cookies -> movie.douban.com -> dbcl2 / ck)')


def fetch(url, cookie):
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Cookie': cookie,
        'Referer': 'https://movie.douban.com/mine',
    })
    with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
        return r.read().decode('utf-8', errors='replace')


def strip_tags(s):
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&quot;', '"')
    return re.sub(r'\s+', ' ', s).strip()


def parse_items(html):
    """grid 模式下每条是一个 div.item.comment-item。"""
    out = []
    chunks = re.split(r'<div class="item comment-item"', html)[1:]
    for chunk in chunks:
        sid = re.search(r'subject/(\d+)/', chunk)
        if not sid:
            continue
        title_block = re.search(r'<li class="title">\s*<a[^>]*>(.*?)</a>', chunk, re.S)
        title = strip_tags(title_block.group(1)) if title_block else ''
        intro = re.search(r'<li class="intro">\s*([^<]*)', chunk)
        info = strip_tags(intro.group(1)) if intro else ''
        rating = re.search(r'<span class="rating(\d)-t">', chunk)
        date = re.search(r'<span class="date">\s*([\d-]+)\s*</span>', chunk)
        comment = re.search(r'<span class="comment">(.*?)</span>', chunk, re.S)
        poster = re.search(r'<img[^>]+src="([^"]+)"', chunk)
        out.append({
            'id': sid.group(1),
            'title': title,
            'info': info,
            'rating': int(rating.group(1)) if rating else 0,
            'date': date.group(1) if date else '',
            'comment': strip_tags(comment.group(1)) if comment else '',
            'poster': poster.group(1) if poster else '',
            'url': 'https://movie.douban.com/subject/%s/' % sid.group(1),
        })
    return out


def total_pages(html):
    m = re.search(r'data-total-page="(\d+)"', html)
    return int(m.group(1)) if m else 0


def collect(url_tpl, max_pages, cookie, label):
    items, total = [], 0
    pages = max_pages
    for p in range(max_pages):
        if p:
            time.sleep(random.uniform(1.5, 3.0))
        try:
            html = fetch(url_tpl % (p * 15), cookie)
        except Exception as e:
            print('  %s page %d fetch error: %s' % (label, p + 1, e))
            break
        if 'TCaptcha' in html or '检测到有异常请求' in html:
            print('  %s CAPTCHA at page %d, stopping' % (label, p + 1))
            break
        if p == 0:
            tp = total_pages(html)
            if tp:
                pages = min(max_pages, tp)
        got = parse_items(html)
        if not got:
            break
        items.extend(got)
        if p == 0 and total_pages(html):
            tp = total_pages(html)
            # 总数 = (总页数-1)*15 + 最后一页条数；最后一页单独取一次
            if tp > pages:
                time.sleep(random.uniform(1.5, 3.0))
                try:
                    last = parse_items(fetch(url_tpl % ((tp - 1) * 15), cookie))
                    total = (tp - 1) * 15 + len(last)
                except Exception:
                    total = tp * 15
            else:
                total = (tp - 1) * 15 + len(got)
        if p + 1 >= pages:
            break
    return items, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--user', default='d2278827')
    ap.add_argument('--pages', type=int, default=4, help='看过列表抓前 N 页（每页 15 条）')
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()

    cookie = load_cookie()
    collect_tpl = ('https://movie.douban.com/people/%s/collect'
                   '?start=%%d&sort=time&mode=grid&type=all&filter=all' % a.user)
    wish_tpl = 'https://movie.douban.com/people/%s/wish?start=%%d&mode=grid' % a.user

    print('fetching watched:', a.pages, 'pages')
    items, watched_total = collect(collect_tpl, a.pages, cookie, 'watched')
    print('  got %d items, total watched %d' % (len(items), watched_total))

    print('fetching wishlist total')
    _wish_items, wish_total = collect(wish_tpl, 1, cookie, 'wish')
    print('  total wish %d' % wish_total)

    if not items:
        print('no items scraped; keep old JSON')
        raise SystemExit(1)

    data = {
        'updated': time.strftime('%Y-%m-%d'),
        'user': a.user,
        'stats': {
            'watched': watched_total or len(items),
            'wish': wish_total,
            'recent_commented': sum(1 for i in items if i['comment']),
        },
        'items': items,
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('wrote', a.out)


if __name__ == '__main__':
    main()
