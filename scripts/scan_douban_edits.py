#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""轮转扫描豆瓣全量「书影音」记录，检测老条目被改过的评分/短评。

主列表 fetch_douban.py 只抓「看过」最近 45 条（按看过日期倒序），给很久以前标过
的电影改评价不会进窗口，站点和动态都看不到。

本脚本走豆瓣 App 的 rexxar 接口（一次 50 条、带 rating/comment/create_time），
每次抓 N 页，把全量状态存进 ~/Projects/个人网站维护/data/douban_snapshot.json，
与上一轮比；发现 rating/comment 变化就写 data/douban_edits.json，供
fetch_activity.py 生成「重新评价」动态。

为什么不用网页列表：网页一页 15 条，124 页；接口一页 50 条，全量约 62 页，
默认每次 8 页 → 约 1.5 天转完一遍。接口的 create_time 是「标记时间」，
改评价不会变，也没有 updated_at，所以只能靠值比对（基线建立之后的改动）。

用法：
    python3 scripts/scan_douban_edits.py [--user d2278827] [--pages 8]
                                         [--snapshot PATH] [--out PATH]
退出码：0 = 正常（含被限流提前结束）；1 = 快照读写失败。
"""
import argparse
import json
import os
import random
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_douban as fd  # noqa: E402  复用 cookie 与 SSL 上下文

ROOT = fd.ROOT
SNAPSHOT = os.path.expanduser('~/Projects/个人网站维护/data/douban_snapshot.json')
OUT = os.path.join(ROOT, 'data', 'douban_edits.json')
API = ('https://m.douban.com/rexxar/api/v2/user/%s/interests'
       '?type=movie&count=50&start=%d')
UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
      'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')
MAX_EVENTS = 30


def load_json(path, default):
    try:
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        return d if isinstance(d, dict) else default
    except FileNotFoundError:
        return default
    except Exception as e:
        print('cannot read %s (%s); starting fresh' % (path, e))
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def norm_comment(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def fetch_page(user, start, cookie):
    req = urllib.request.Request(API % (user, start), headers={
        'User-Agent': UA,
        'Cookie': cookie,
        'Referer': 'https://m.douban.com/movie/people/%s/collect' % user,
    })
    with urllib.request.urlopen(req, timeout=40, context=fd.CTX) as r:
        return json.loads(r.read().decode('utf-8', 'replace'))


def compare(interests, snap, detected):
    """把这一页和快照比，更新快照，返回被改过的条目。

    snap 结构：{subject_id: {"rating": int, "comment": str, "date": str}}
    第一次见到的条目只入快照，不算改动。
    """
    events = []
    for it in interests:
        subj = it.get('subject') or {}
        sid = str(subj.get('id') or '')
        if not sid:
            continue
        cur = {
            'rating': int((it.get('rating') or {}).get('star_count') or 0),
            'comment': norm_comment(it.get('comment')),
            'date': (it.get('create_time') or '')[:10],
        }
        old = snap.get(sid)
        snap[sid] = cur
        if old is None:
            continue
        if int(old.get('rating') or 0) == cur['rating'] and \
                norm_comment(old.get('comment')) == cur['comment']:
            continue
        title = (subj.get('title') or '').strip()[:80] or sid
        events.append({
            'id': sid,
            'title': title,
            'rating': cur['rating'],
            'old_rating': int(old.get('rating') or 0),
            'comment_changed': norm_comment(old.get('comment')) != cur['comment'],
            'date': cur['date'],
            'detected': detected,
        })
    return events


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--user', default='d2278827')
    ap.add_argument('--pages', type=int, default=8, help='本次抓几页（每页 50 条）')
    ap.add_argument('--snapshot', default=SNAPSHOT)
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()

    state = load_json(a.snapshot, {})
    snap = state.get('items') or {}
    total = int(state.get('total') or 0)
    start = int(state.get('next_start') or 0)

    cookie = fd.load_cookie()
    detected = time.strftime('%Y-%m-%d %H:%M')
    events, scanned = [], 0

    for _ in range(a.pages):
        try:
            data = fetch_page(a.user, start, cookie)
        except Exception as e:
            print('page at %d failed: %s' % (start, e))
            break
        total = int(data.get('total') or total or 0)
        interests = data.get('interests') or []
        if not interests:
            print('empty page at %d; stopping' % start)
            break
        events += compare(interests, snap, detected)
        scanned += 1
        start += len(interests)
        if total and start >= total:
            start = 0
        time.sleep(random.uniform(0.6, 1.2))

    try:
        save_json(a.snapshot, {
            'updated': detected,
            'source': 'rexxar/interests',
            'total': total,
            'next_start': start,
            'items': snap,
        })
    except Exception as e:
        print('cannot write snapshot: %s' % e)
        return 1

    old = load_json(a.out, {}).get('items') or []
    seen = {(e.get('id'), e.get('detected')) for e in events}
    merged = events + [e for e in old if (e.get('id'), e.get('detected')) not in seen]
    if events or old:
        try:
            save_json(a.out, {
                'updated': time.strftime('%Y-%m-%d'),
                'items': merged[:MAX_EVENTS],
            })
        except Exception as e:
            print('cannot write edits: %s' % e)
            return 1

    print('scanned %d page(s) up to %d/%d; snapshot %d items; %d edit(s)'
          % (scanned, start, total or 0, len(snap), len(events)))
    for e in events[:5]:
        print('  * %s (%s): %d -> %d%s'
              % (e['title'], e['date'], e['old_rating'], e['rating'],
                 ', comment changed' if e['comment_changed'] else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
