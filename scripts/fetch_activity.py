#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从本机自建的 RSSHub 抓「动态」源，合并成 data/activity.json。

RSSHub（Docker）：docker run -d --name rsshub -p 1200:1200 --env-file ~/rsshub.env diygod/rsshub
默认地址 http://127.0.0.1:1200，可用环境变量 RSSHUB_BASE 覆盖。

用法：
    python3 scripts/fetch_activity.py [--per-source 15] [--keep 30]

抓取失败时保留上一份 JSON 并退出码 1（与 fetch_data.py / fetch_douban.py 同口径）。
"""
import argparse
import html
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

if getattr(sys.stdout, 'encoding', None) not in (None, 'utf-8'):
    import io
    if sys.stdout:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'activity.json')
BASE = os.environ.get('RSSHUB_BASE', 'http://127.0.0.1:1200').rstrip('/')

# 想加源就往这里加：key 用于前端分类与图标
SOURCES = [
    # 豆瓣广播路由只认整数型 id（字母型 d2278827 会 404）：
    # 从 https://www.douban.com/people/<id>/ 的头像链接 ul122411510-*.jpg 取 122411510
    {'key': 'douban', 'label': '豆瓣', 'route': '/douban/people/122411510/status'},
    {'key': 'github', 'label': 'GitHub', 'route': '/github/activity/yanghaod2278827'},
    {'key': 'bilibili', 'label': 'B站', 'route': '/bilibili/user/video/357798787'},
]


# 本站仓库的 push 不记进动态：否则「同步脚本提交数据 → 部署 → 产生新 push 事件
# → 数据又变」会形成自激循环（每轮都产生新条目）。要记录自己的提交就把它移出这里。
EXCLUDE_REPOS = {'yanghaod2278827.github.io'}

TAG_RE = re.compile(r'<[^>]+>')
TZ = timezone(timedelta(hours=8))


def localize(iso):
    """RSSHub 的 date_published 是 UTC，转成 +08:00 再截到分钟。"""
    if not iso:
        return ''
    try:
        dt = datetime.fromisoformat(iso.replace('Z', '+00:00'))
        return dt.astimezone(TZ).strftime('%Y-%m-%d %H:%M')
    except Exception:
        return iso[:16].replace('T', ' ')


def fetch(route, per_source, source=''):
    url = '%s%s?format=json&limit=%d' % (BASE, route, per_source)
    # RSSHub 的路由偶尔 503（上游站点抽风），重试一次再放弃
    last = None
    data = None
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'personal-site-activity/1.0'})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read().decode('utf-8', 'replace'))
            break
        except Exception as e:
            last = e
            if attempt == 0:
                time.sleep(6)
    if data is None:
        raise last
    items = data.get('items') or []
    out = []
    for it in items:
        raw_title = (it.get('title') or '').strip()
        desc = it.get('description') or it.get('content_html') or ''
        text = html.unescape(TAG_RE.sub(' ', desc))
        text = re.sub(r'\s+', ' ', text).strip()

        # 豆瓣「看过」的 title 形如「杨浩 看过: 《片名 原名 (年)》短评」——
        # 片名单独拿出来当标题，短评当正文，避免正文里重复一遍片名和影片信息
        title, film = raw_title, ''
        m = re.search(r'《(.+?)》', raw_title)
        if m:
            film = m.group(1).split('  ')[0].split(' / ')[0].strip()
            rest = raw_title.split('》', 1)[1].strip() if '》' in raw_title else ''
            title = film
            text = rest  # 没短评就留空，别把影片信息当正文
        if not text and not film:
            text = raw_title

        # GitHub 的 activity 事件标题是「<user> pushed <repo>」且同一仓库一天会连发多条，
        # 这里统一成仓库名，正文留空，后面再按 (源, 标题, 日期) 合并计数
        # 正文清洗：去掉裸链接、占位符，以及和标题重复的内容
        text = re.sub(r'https?://\S+', '', text).strip()
        if text in ('-', '—', '.', '…'):
            text = ''
        norm = lambda x: re.sub(r'[\s\W_]+', '', x).lower()
        if text and title:
            nt, nx = norm(title)[:24], norm(text)[:24]
            if nt and (nx.startswith(nt) or nt.startswith(nx) or nx in norm(title)):
                text = ''
        if not title and text:
            title, text = text[:60], ''

        if source == 'github':
            m_repo = re.search(r'github\.com/[^/]+/([^/]+)', it.get('url') or '')
            if m_repo:
                repo = m_repo.group(1)
                if repo in EXCLUDE_REPOS:
                    continue  # 见 EXCLUDE_REPOS 的说明，避免自激
                title, text = repo, ''

        out.append({
            'title': title[:120],
            'film': film,
            'text': text[:600],
            'link': (it.get('url') or it.get('link') or '').strip(),
            'date': localize(it.get('date_published') or it.get('pubDate') or ''),
            'image': it.get('image') or '',
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--per-source', type=int, default=15)
    ap.add_argument('--keep', type=int, default=30)
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()

    merged, failed = [], []
    for s in SOURCES:
        try:
            got = fetch(s['route'], a.per_source, s['key'])
            for it in got:
                it['source'] = s['key']
                it['source_label'] = s['label']
            merged.extend(got)
            print('%-8s %d items' % (s['key'], len(got)))
        except Exception as e:
            failed.append('%s: %s' % (s['key'], e))
            print('%-8s FAILED: %s' % (s['key'], e))

    if failed and not merged:
        print('all sources failed; keep old JSON')
        raise SystemExit(1)

    def merge_same_day(items):
        """同一源、同一标题、同一天的多条合并成一条，记 count。"""
        seen, out = {}, []
        for it in items:
            k = (it.get('source'), it.get('title'), (it.get('date') or '')[:10])
            if k in seen:
                seen[k]['count'] = seen[k].get('count', 1) + 1
                continue
            it['count'] = 1
            seen[k] = it
            out.append(it)
        return out

    merged = merge_same_day(merged)

    def key(it):
        d = it.get('date') or ''
        return d

    merged.sort(key=key, reverse=True)
    merged = merged[:a.keep]

    data = {
        'updated': __import__('time').strftime('%Y-%m-%d'),
        'sources': [s['key'] for s in SOURCES if s['key'] not in [f.split(':')[0] for f in failed]],
        'items': merged,
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('wrote %s (%d items)' % (a.out, len(merged)))


if __name__ == '__main__':
    main()
