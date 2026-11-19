#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为每篇文章生成一张 1200×1200 的封面图（真实 PNG，不是 CSS 占位）。

风格跟站点一致：虚线方格底 + 标题首字 + 标题 + 分类标签，
色相由标题哈希决定（与 post-cover.html 的算法一致，换模板也保持同色）。

用法：
    python3 scripts/make_covers.py [--out static/images/covers]

生成后在文章 front matter 里写 `cover: /images/covers/<slug>.png`。
需要本地已装 playwright（Chromium）。
"""
import argparse
import glob
import hashlib
import io
import os
import re
import sys

if getattr(sys.stdout, 'encoding', None) not in (None, 'utf-8'):
    if sys.stdout:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEMPLATE = '''<!doctype html><html><head><meta charset="utf-8"><style>
  html, body {{ margin: 0; width: 1200px; height: 1200px; }}
  body {{
    position: relative; overflow: hidden; background: #ffffff; color: #0a0a0a;
    font-family: ui-sans-serif, system-ui, "Microsoft YaHei", "PingFang SC", sans-serif;
  }}
  .grid {{
    position: absolute; inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='96' height='96'%3E%3Cpath d='M0 .5H96M.5 0V96' fill='none' stroke='%23d4d4d4' stroke-width='1' stroke-dasharray='4 6'/%3E%3C/svg%3E");
    -webkit-mask-image: radial-gradient(115% 85% at 0% 0%, #000 8%, transparent 72%);
    mask-image: radial-gradient(115% 85% at 0% 0%, #000 8%, transparent 72%);
  }}
  .wrap {{ position: absolute; inset: 0; padding: 72px; display: flex; flex-direction: column; justify-content: space-between; }}
  .glyph {{
    font-size: 560px; font-weight: 700; line-height: .82; letter-spacing: -.06em;
    color: hsl({hue} 42% 36%); margin-left: -14px;
  }}
  .foot {{ display: flex; align-items: center; justify-content: space-between; }}
  .tag {{
    padding: 10px 26px; border: 3px dashed hsl({hue} 32% 74%); border-radius: 999px;
    font-size: 34px; color: hsl({hue} 28% 42%);
  }}
  .date {{ font-size: 30px; color: #8a8a8a; font-variant-numeric: tabular-nums;
           font-family: ui-monospace, Menlo, Consolas, monospace; }}
</style></head><body>
  <div class="grid"></div>
  <div class="wrap">
    <div class="glyph">{glyph}</div>
    <div class="foot"><span class="tag">{category}</span><span class="date">{date}</span></div>
  </div>
</body></html>'''


def read_front_matter(path):
    """极简 front matter 解析：只要 title / slug / date / categories。"""
    txt = open(path, encoding='utf-8').read()
    m = re.match(r'^---\n(.*?)\n---', txt, re.S)
    fm = m.group(1) if m else ''
    def get(key):
        mm = re.search(r'^%s:\s*(.*)$' % key, fm, re.M)
        return mm.group(1).strip().strip('"') if mm else ''
    cats = re.search(r'^categories:\s*\[(.*?)\]', fm, re.M)
    category = cats.group(1).split(',')[0].strip().strip('"') if cats else ''
    return {
        'title': get('title'),
        'slug': get('slug') or os.path.splitext(os.path.basename(path))[0],
        'date': get('date'),
        'category': category,
    }


def hue_of(title):
    # 与 Hugo 的 hash.FNV32a 不同，但同样稳定：只要不换算法，同一篇永远同色
    h = int(hashlib.md5(title.encode('utf-8')).hexdigest(), 16)
    return h % 360


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(ROOT, 'static', 'images', 'covers'))
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    langs = [('zh', os.path.join(ROOT, 'content', 'zh', 'posts')),
             ('en', os.path.join(ROOT, 'content', 'en', 'posts'))]

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': 1200, 'height': 1200}, device_scale_factor=1)
        for lang, cdir in langs:
            odir = os.path.join(a.out, lang)
            os.makedirs(odir, exist_ok=True)
            posts = [read_front_matter(p) for p in sorted(glob.glob(os.path.join(cdir, '*.md')))
                     if not os.path.basename(p).startswith('_')]
            for post in posts:
                out = os.path.join(odir, post['slug'] + '.png')
                if os.path.exists(out) and not a.force:
                    print('skip (exists)', out)
                    continue
                g = post['title'][:1]
                if lang == 'en':
                    g = g.upper()
                html = TEMPLATE.format(
                    hue=hue_of(post['title']),
                    glyph=g,
                    category=post['category'] or ('Posts' if lang == 'en' else '博客'),
                    date=post['date'],
                )
                page.set_content(html, wait_until='load')
                page.wait_for_timeout(120)
                page.screenshot(path=out)
                print('wrote', out)
        # 项目卡封面：名字首字母 + 语言标签（与文章封面同一套版式）
        import json as _json
        proj_json = os.path.join(ROOT, 'data', 'projects.json')
        if os.path.exists(proj_json):
            pdir = os.path.join(a.out, 'projects')
            os.makedirs(pdir, exist_ok=True)
            for proj in _json.load(open(proj_json, encoding='utf-8')):
                out = os.path.join(pdir, proj['name'] + '.png')
                if os.path.exists(out) and not a.force:
                    print('skip (exists)', out)
                    continue
                parts = re.split(r'[._-]', proj['name'])
                glyph = ''.join(x[:1] for x in parts[:2]).upper()
                html = TEMPLATE.format(
                    hue=hue_of(proj['name']),
                    glyph=glyph,
                    category=proj.get('language') or 'Repo',
                    date='',
                )
                page.set_content(html, wait_until='load')
                page.wait_for_timeout(120)
                page.screenshot(path=out)
                print('wrote', out)
        browser.close()


if __name__ == '__main__':
    main()
