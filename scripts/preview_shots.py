#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对构建产物截图（明/暗两套），用于改版后目检。

用法：
    python3 scripts/preview_shots.py [--port 8765] [--out 报告/预览]

先用 `hugo --gc --minify` 生成 public/，脚本自己起一个静态服务器。
"""
import argparse
import functools
import http.server
import os
import socketserver
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUBLIC = os.path.join(ROOT, 'public')

PAGES = [
    ('home-zh', '/'),
    ('posts-zh', '/posts/'),
    ('post-zh', '/posts/2026/11/claude-worklog-dida/'),
    ('projects-zh', '/projects/'),
    ('movies-zh', '/movies/'),
    ('home-en', '/en/'),
]


def serve(port):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=PUBLIC)
    httpd = socketserver.TCPServer(('127.0.0.1', port), handler)
    httpd.allow_reuse_address = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--out', default=os.path.join(ROOT, '报告', '预览'))
    ap.add_argument('--width', type=int, default=1280)
    ap.add_argument('--height', type=int, default=900)
    ap.add_argument('--mobile', action='store_true', help='用 390x844 手机视口再截一套（-m 后缀）')
    a = ap.parse_args()

    if not os.path.isdir(PUBLIC):
        raise SystemExit('public/ 不存在，先跑 hugo --gc --minify')
    os.makedirs(a.out, exist_ok=True)

    from playwright.sync_api import sync_playwright

    httpd = serve(a.port)
    base = 'http://127.0.0.1:%d' % a.port
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={'width': a.width, 'height': a.height},
                                    device_scale_factor=1)
            for scheme in ('light', 'dark'):
                page.emulate_media(color_scheme=scheme)
                # 主题初始化脚本会读 localStorage；显式清掉，保证按 color-scheme 走
                page.add_init_script("try{localStorage.removeItem('theme')}catch(e){}")
                for name, path in PAGES:
                    page.goto(base + path, wait_until='networkidle')
                    page.wait_for_timeout(200)
                    fn = os.path.join(a.out, '%s-%s.png' % (name, scheme))
                    page.screenshot(path=fn, full_page=True)
                    print('wrote', fn)
            if a.mobile:
                m = browser.new_page(viewport={'width': 390, 'height': 844})
                for scheme in ('light', 'dark'):
                    m.emulate_media(color_scheme=scheme)
                    m.add_init_script("try{localStorage.removeItem('theme')}catch(e){}")
                    for name, path in PAGES[:3]:
                        m.goto(base + path, wait_until='networkidle')
                        m.wait_for_timeout(200)
                        fn = os.path.join(a.out, '%s-%s-m.png' % (name, scheme))
                        m.screenshot(path=fn, full_page=True)
                        print('wrote', fn)
            browser.close()
    finally:
        httpd.shutdown()


if __name__ == '__main__':
    if sys.stdout.encoding != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    main()
