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
    {'key': 'netease', 'label': '网易云', 'route': '/163/music/user/events/131590947'},
    # 「我喜欢的音乐」没有 RSSHub 路由（interests/like 类都已删除），
    # 这里直接查网易云公开接口 + 本地状态做 diff：只在有新收藏时才产出条目
    {'key': 'netease_liked', 'label': '网易云', 'type': 'netease_liked',
     'playlist': 165468638, 'uid': 131590947},
]

STATE_DIR = os.environ.get('ACTIVITY_STATE_DIR', os.path.expanduser('~/.cache/personal-site-activity'))
LIKED_STATE = os.path.join(STATE_DIR, 'netease_liked.json')

def fetch_liked_songs(playlist_id):
    """拉「我喜欢的音乐」歌单：总数、更新时间、最新若干首。

    未登录时网易云只回前 6 首，但 trackCount / trackUpdateTime 是公开的，
    所以即使看不到全量，也能靠**总数增减**判断「新增/取消收藏」。
    """
    ck = os.environ.get('NCM_COOKIE', '').strip()
    if not ck:
        for cand in ('~/netease_cookie.txt', '~/.netease_cookie'):
            fp = os.path.expanduser(cand)
            if os.path.exists(fp):
                ck = open(fp, encoding='utf-8').read().strip()
                break
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                             '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
               'Referer': 'https://music.163.com/'}
    if ck:
        headers['Cookie'] = ck
    url = 'https://music.163.com/api/v6/playlist/detail?id=%s' % playlist_id
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=40) as r:
        data = json.loads(r.read().decode('utf-8', 'replace'))
    pl = data.get('playlist') or {}
    tracks = []
    for t in (pl.get('tracks') or [])[:10]:
        ars = t.get('ar') or t.get('artists') or []
        tracks.append({
            'id': str(t.get('id')),
            'name': t.get('name') or '',
            'artists': '/'.join(a.get('name', '') for a in ars),
        })
    ts = pl.get('trackUpdateTime') or pl.get('updateTime')
    return {
        'count': int(pl.get('trackCount') or len(tracks)),
        'ts': ts,
        'tracks': tracks,
        'has_cookie': bool(ck),
    }


def liked_events(snap, playlist_id):
    """对比上次快照，产出「喜欢/取消喜欢」事件。

    日期取歌单的 trackUpdateTime（真实变动时刻），不是发现时刻。
    """
    os.makedirs(STATE_DIR, exist_ok=True)
    prev = None
    if os.path.exists(LIKED_STATE):
        try:
            prev = json.load(open(LIKED_STATE, encoding='utf-8'))
        except Exception:
            prev = None

    pl_url = 'https://music.163.com/playlist?id=%s' % playlist_id
    if snap.get('ts'):
        when = datetime.fromtimestamp(snap['ts'] / 1000).strftime('%Y-%m-%d %H:%M')
    else:
        when = time.strftime('%Y-%m-%d %H:%M')

    events = []
    ids_now = [t['id'] for t in snap['tracks']]
    state = {'count': snap['count'], 'ids': ids_now, 'updated': when}

    if prev and isinstance(prev.get('count'), int):
        delta = snap['count'] - prev['count']
        known = set(prev.get('ids') or [])
        if delta > 0:
            new = [t for t in snap['tracks'] if t['id'] not in known]
            for t in new:
                events.append({
                    'title': ('♥ 喜欢了《%s》— %s' % (t['name'], t['artists'])) if t['artists']
                             else ('♥ 喜欢了《%s》' % t['name']),
                    'film': '', 'text': '',
                    'link': 'https://music.163.com/song?id=%s' % t['id'],
                    'date': when, 'image': '',
                })
            if delta > len(new):
                events.append({'title': '♥ 喜欢了 %d 首歌' % delta, 'film': '', 'text': '',
                               'link': pl_url, 'date': when, 'image': ''})
        elif delta < 0:
            events.append({'title': '♡ 取消了 %d 首收藏' % (-delta), 'film': '', 'text': '',
                           'link': pl_url, 'date': when, 'image': ''})
    else:
        print('netease_liked snapshot initialised (%d songs), no items emitted' % snap['count'])

    json.dump(state, open(LIKED_STATE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    return events


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
    req = urllib.request.Request(url, headers={'User-Agent': 'personal-site-activity/1.0'})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode('utf-8', 'replace'))
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
                title, text = m_repo.group(1), ''

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
            if s.get('type') == 'netease_liked':
                snap = fetch_liked_songs(s['playlist'])
                got = liked_events(snap, s['playlist'])
                print('%-8s %d songs (cookie=%s), %d events'
                      % (s['key'], snap['count'], snap['has_cookie'], len(got)))
            else:
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
