#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抓抖音主页的最近作品 → data/douyin.json（供「动态」时间线读取）。

抖音网页端有签名（a_bogus）和登录校验，没有可直接调的公开接口，所以这里用
Playwright 打开个人主页，**拦截页面自己发出的** `/aweme/v1/web/aweme/post/`
响应——签名由页面自己算，我们只取结果。

Cookie 不进仓库：读环境变量 `DOUYIN_COOKIES`（Netscape 格式文件路径）或
`~/douyin_cookies.txt`（浏览器扩展导出的 cookie.txt）。过期表现是抓不到
post 响应，重新导出一次即可。

用法：
    python3 scripts/fetch_douyin.py [--sec-uid ...] [--out data/douyin.json]
"""
import argparse
import json
import os
import sys
import time

if getattr(sys.stdout, 'encoding', None) not in (None, 'utf-8'):
    import io
    if sys.stdout:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'douyin.json')
DEFAULT_SEC_UID = 'MS4wLjABAAAA23-trcRF6O0CgMplB8ae7Ryt2utjgKi1xcubyDvLir0'
PAGE_URL = 'https://www.douyin.com/user/%s'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')


def cookie_path():
    p = os.environ.get('DOUYIN_COOKIES', '').strip()
    if p and os.path.exists(p):
        return p
    for cand in ('~/douyin_cookies.txt', '~/.douyin_cookies.txt'):
        fp = os.path.expanduser(cand)
        if os.path.exists(fp):
            return fp
    raise SystemExit('missing Douyin cookies: export them (Netscape format) to ~/douyin_cookies.txt')


def load_cookies(path):
    """Netscape 格式：domain \t flag \t path \t secure \t expiry \t name \t value"""
    out = []
    for line in open(path, encoding='utf-8', errors='replace'):
        line = line.rstrip('\n')
        if line.startswith('#HttpOnly_'):
            line = line[len('#HttpOnly_'):]
        elif line.startswith('#') or not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) >= 7 and parts[5]:
            out.append({
                'domain': parts[0],
                'path': parts[2] or '/',
                'name': parts[5],
                'value': parts[6],
            })
    if not out:
        raise SystemExit('cookie file parsed to zero entries')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sec-uid', default=DEFAULT_SEC_UID)
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()

    cookies = load_cookies(cookie_path())

    from playwright.sync_api import sync_playwright

    captured = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(user_agent=UA)
        ctx.add_cookies(cookies)
        page = ctx.new_page()

        def on_response(resp):
            if '/aweme/v1/web/aweme/post/' in resp.url:
                try:
                    captured.append(resp.json())
                except Exception:
                    pass

        page.on('response', on_response)
        # 图片/字体/视频会拖慢加载，也会让抖音的风控更容易触发
        page.route('**/*', lambda r: r.abort()
                   if r.request.resource_type in ('image', 'font', 'media') else r.continue_())
        page.goto(PAGE_URL % a.sec_uid, wait_until='domcontentloaded', timeout=60000)
        page.wait_for_timeout(9000)
        browser.close()

    items, seen = [], set()
    for payload in captured:
        for w in (payload.get('aweme_list') or []):
            aid = w.get('aweme_id')
            if not aid or aid in seen:
                continue
            seen.add(aid)
            stats = w.get('statistics') or {}
            items.append({
                'id': aid,
                'desc': (w.get('desc') or '').strip(),
                'date': time.strftime('%Y-%m-%d %H:%M', time.localtime(w.get('create_time') or 0)),
                'url': 'https://www.douyin.com/video/%s' % aid,
                'digg': stats.get('digg_count') or 0,
                'comment': stats.get('comment_count') or 0,
            })

    if not items:
        print('no posts captured (cookies expired or Douyin changed its page)')
        raise SystemExit(1)

    items.sort(key=lambda x: x['date'], reverse=True)
    payload = {
        'updated': time.strftime('%Y-%m-%d'),
        'sec_uid': a.sec_uid,
        'count': len(items),
        'items': items,
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print('%d posts -> %s' % (len(items), a.out))


if __name__ == '__main__':
    main()
