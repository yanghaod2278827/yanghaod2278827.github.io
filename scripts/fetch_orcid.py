#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 ORCID 公开 API 抓「已发表论文」清单 → data/publications.json。

ORCID 的公开记录由 Crossref 自动回填，所以这里列的都是已正式发表、有 DOI 的条目
（在投稿件不会出现），适合直接公开展示。

用法：
    python3 scripts/fetch_orcid.py [--orcid 0009-0001-7869-3957]

抓取失败时保留上一份 JSON 并退出码 1（与其它抓取脚本同口径）。
"""
import argparse
import json
import os
import ssl
import sys
import urllib.request

if getattr(sys.stdout, 'encoding', None) not in (None, 'utf-8'):
    import io
    if sys.stdout:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'publications.json')
DEFAULT_ORCID = '0009-0001-7869-3957'

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def get(url):
    req = urllib.request.Request(url, headers={
        'Accept': 'application/json',
        'User-Agent': 'personal-site/1.0 (+https://yanghaod2278827.github.io/)',
    })
    with urllib.request.urlopen(req, timeout=45, context=CTX) as r:
        return json.loads(r.read().decode('utf-8', 'replace'))


def pick_ids(work):
    doi, url = '', ''
    for ext in ((work.get('external-ids') or {}).get('external-id') or []):
        if ext.get('external-id-type') == 'doi':
            doi = (ext.get('external-id-value') or '').strip()
            eu = ext.get('external-id-url') or {}
            url = (eu.get('value') or '').strip()
            break
    if not url:
        url = ((work.get('url') or {}).get('value') or '').strip()
    if not url and doi:
        url = 'https://doi.org/' + doi
    return doi, url


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--orcid', default=DEFAULT_ORCID)
    ap.add_argument('--out', default=OUT)
    a = ap.parse_args()

    try:
        data = get('https://pub.orcid.org/v3.0/%s/works' % a.orcid)
    except Exception as e:
        print('ORCID fetch failed: %s (keeping previous data)' % e)
        raise SystemExit(1)

    items = []
    for group in data.get('group') or []:
        summaries = group.get('work-summary') or []
        if not summaries:
            continue
        # 同一作品可能有多个 source，取第一个（Crossref 优先）
        w = sorted(summaries, key=lambda s: 0 if ((s.get('source') or {}).get('source-name') or {}).get('value') == 'Crossref' else 1)[0]
        title = ((w.get('title') or {}).get('title') or {}).get('value') or ''
        journal = ((w.get('journal-title') or {}).get('value') or '')
        year = str(((w.get('publication-date') or {}).get('year') or {}).get('value') or '')
        doi, url = pick_ids(w)
        if not title:
            continue
        items.append({
            'title': title.strip(),
            'journal': journal.strip(),
            'year': year,
            'type': (w.get('type') or 'journal-article'),
            'doi': doi,
            'url': url,
        })

    items.sort(key=lambda x: (x['year'], x['title']), reverse=True)

    payload = {'orcid': a.orcid, 'count': len(items), 'items': items}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print('%d works -> %s' % (len(items), a.out))


if __name__ == '__main__':
    main()
