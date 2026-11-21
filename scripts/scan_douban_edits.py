#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""轮转扫描豆瓣「看过」全量列表，检测老条目被改过的评分/短评。

主列表 fetch_douban.py 只抓最近 45 条（按看过日期倒序），给很久以前标过的电影
改评价不会进窗口，站点和动态都看不到。本脚本每次抓 N 页（默认 3），把全量条目
的最新状态存进 ~/Projects/个人网站维护/data/douban_snapshot.json，与上一轮比；
发现 rating / comment / date 变化就写 data/douban_edits.json，供
fetch_activity.py 生成「重新评价」动态。

124 页、每次 3 页、每天按 4 小时节流跑一轮 → 约一周转完一遍全量。

用法：
    python3 scripts/scan_douban_edits.py [--user d2278827] [--pages 3]
                                         [--snapshot PATH] [--out PATH]
退出码：0 = 正常（含被频控提前结束）；1 = 快照读写失败。
"""
import argparse
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_douban as fd  # noqa: E402  复用 cookie / 抓取 / 解析

ROOT = fd.ROOT
SNAPSHOT = os.path.expanduser('~/Projects/个人网站维护/data/douban_snapshot.json')
OUT = os.path.join(ROOT, 'data', 'douban_edits.json')
TPL = ('https://movie.douban.com/people/%s/collect'
       '?start=%%d&sort=time&mode=grid&type=all&filter=all')
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


def compare(page_items, snap, detected):
    """把这一页和快照比，更新快照，返回被改过的条目。

    snap 结构：{subject_id: {"rating": int, "date": str, "comment": str}}
    第一次见到的条目只入快照，不算改动。
    """
    events = []
    for it in page_items:
        sid = it.get('id')
        if not sid:
            continue
        cur = {
            'rating': int(it.get('rating') or 0),
            'date': (it.get('date') or '')[:10],
            'comment': (it.get('comment') or '').strip(),
        }
        old = snap.get(sid)
        snap[sid] = cur
        if old is None or old == cur:
            continue
        title = (it.get('title') or '').split(' / ')[0].strip()[:80]
        events.append({
            'id': sid,
            'title': title or sid,
            'rating': cur['rating'],
            'old_rating': int(old.get('rating') or 0),
            'comment_changed': (old.get('comment') or '') != cur['comment'],
            'date': cur['date'],
            'detected': detected,
        })
    return events


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--user', default='d2278827')
    ap.add_argument('--pages', type=int, default=3, help='本次扫几页（每页 15 条）')
    ap.add_argument('--snapshot', default=SNAPSHOT)
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()

    state = load_json(a.snapshot, {})
    snap = state.get('items') or {}
    total = int(state.get('total_pages') or 0)
    page = int(state.get('next_page') or 0)

    cookie = fd.load_cookie()
    detected = time.strftime('%Y-%m-%d %H:%M')
    events, scanned = [], []

    for _ in range(a.pages):
        try:
            html = fd.fetch((TPL % a.user) % (page * 15), cookie)
        except Exception as e:
            print('page %d fetch error: %s' % (page + 1, e))
            break
        if 'TCaptcha' in html or '检测到有异常请求' in html:
            print('CAPTCHA at page %d; stopping' % (page + 1))
            break
        tp = fd.total_pages(html)
        if tp:
            total = tp
        items = fd.parse_items(html)
        if not items:
            print('page %d empty; stopping' % (page + 1))
            break
        events += compare(items, snap, detected)
        scanned.append(page + 1)  # 1-based，便于读日志
        page += 1
        if total and page >= total:
            page = 0
        time.sleep(random.uniform(1.5, 3.0))

    try:
        save_json(a.snapshot, {
            'updated': detected,
            'total_pages': total,
            'next_page': page,
            'items': snap,
        })
    except Exception as e:
        print('cannot write snapshot: %s' % e)
        return 1

    # 合并进 douban_edits.json（保留最近 MAX_EVENTS 条；同一条目同一次检测不重复）
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

    span = ('%d-%d' % (scanned[0], scanned[-1])) if scanned else 'none'
    print('scanned pages %s of %d; snapshot %d items; %d edit(s)'
          % (span, total or 0, len(snap), len(events)))
    for e in events[:5]:
        print('  * %s (%s): %d -> %d%s'
              % (e['title'], e['date'], e['old_rating'], e['rating'],
                 ', comment changed' if e['comment_changed'] else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
