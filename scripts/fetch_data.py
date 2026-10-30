#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 data/github.json 和 data/projects.json。

    GITHUB_TOKEN=xxx python3 scripts/fetch_data.py

Actions 里不需要手动给 token（GITHUB_TOKEN 是自动注入的）。本地不带 token
也能跑，只是有 60 次/小时的匿名限额——足够一次调用。

数据在构建前生成，模板直接读 site.Data.github / site.Data.projects。
"""
import sys, io, os, json, subprocess, urllib.request, urllib.error

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

USER = os.environ.get('GH_USER') or 'yanghaod2278827'
TOKEN = os.environ.get('GITHUB_TOKEN') or os.environ.get('GH_TOKEN') or ''
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
MAX_PROJECTS = 12


def _via_urllib(url):
    req = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'personal-site-data-fetcher',
        **({'Authorization': 'Bearer ' + TOKEN} if TOKEN else {}),
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode('utf-8'))


def _via_gh(url):
    """Fallback for machines where urllib can't verify TLS.

    FastGithub (and some corporate proxies) MITM api.github.com with a cert that
    lives in the Windows store — Go honours that store, Python's bundled certifi
    does not. `gh` already works there, so reuse its transport.
    """
    out = subprocess.run(['gh', 'api', url], capture_output=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.decode('utf-8', 'replace').strip()
                           or 'gh api failed')
    return json.loads(out.stdout.decode('utf-8'))


def api(url):
    try:
        return _via_urllib(url)
    except Exception as e:
        if 'CERTIFICATE' in str(e) or 'SSL' in str(e):
            print('urllib TLS failed (%s) — falling back to gh' % type(e).__name__)
            return _via_gh(url)
        raise


def write(name, obj):
    os.makedirs(DATA, exist_ok=True)
    path = os.path.join(DATA, name)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('wrote %s' % path)


def main():
    try:
        user = api('https://api.github.com/users/%s' % USER)
        repos = api('https://api.github.com/users/%s/repos?per_page=100&sort=updated' % USER)
    except urllib.error.HTTPError as e:
        # 失败时保留上一次的 JSON，别让构建因为网络问题挂掉
        sys.exit('GitHub API %s: %s (keeping previous data)' % (e.code, e.reason))
    except Exception as e:
        sys.exit('%s: %s (keeping previous data)' % (type(e).__name__, e))

    # 只统计自己的仓库：排除 fork、归档，以及与用户名同名的 profile 仓库
    own = [r for r in repos
           if not r.get('fork') and not r.get('archived') and r.get('name') != USER]

    write('github.json', {
        'login': user.get('login'),
        'own_repos': len(own),
        'followers': user.get('followers', 0),
        'total_stars': sum(r.get('stargazers_count', 0) for r in own),
        'updated': __import__('datetime').datetime.now().strftime('%Y-%m-%d'),
    })

    top = sorted(own, key=lambda r: (-r.get('stargazers_count', 0), r.get('name', '')))
    projects = [{
        'name': r['name'],
        'url': r['html_url'],
        'description': r.get('description') or '',
        'language': r.get('language') or '',
        'stars': r.get('stargazers_count', 0),
    } for r in top[:MAX_PROJECTS]]
    write('projects.json', projects)
    print('%d repos -> %d cards, %d stars total'
          % (len(own), len(projects), sum(r.get('stargazers_count', 0) for r in own)))


if __name__ == '__main__':
    main()
