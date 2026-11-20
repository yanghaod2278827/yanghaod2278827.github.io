---
title: Scraping Douyin by letting the page sign its own requests
slug: douyin-playwright-intercepted-api
date: 2026-11-20
tags: ["Douyin", "Playwright", "Scraping"]
---

I wanted my Douyin videos in the site's activity timeline. RSSHub does have `/douyin/user/:sec_uid`, but it is unusable here:

```ts
features: { requirePuppeteer: true, antiCrawler: true }
```

The stock container ships no Chromium, and the web API is signed (`a_bogus` and friends) — hand-crafting requests is a dead end.

## The approach: be a spectator, not a client

Open the profile with Playwright and **let the page make its own requests**, then intercept the response:

```python
captured = []
page.on('response', lambda r: captured.append(r.json())
        if '/aweme/v1/web/aweme/post/' in r.url else None)

page.route('**/*', lambda r: r.abort()
           if r.request.resource_type in ('image', 'font', 'media') else r.continue_())

page.goto('https://www.douyin.com/user/<sec_uid>', wait_until='domcontentloaded')
page.wait_for_timeout(8000)
```

The page's JS computes the signature, the context supplies cookies, the page issues the request — all we do is parse `aweme_list`.

## The prerequisite: cookies

Unlike Douban, everything else is discoverable (`sec_uid` is literally in the profile URL), but a **logged-in cookie** is mandatory: without it the page loads and simply never requests the posts — the listener fires zero times.

Export cookies in Netscape format from a browser extension and parse them directly:

```python
for line in open(path):
    if line.startswith('#HttpOnly_'): line = line[len('#HttpOnly_'):]
    elif line.startswith('#'): continue
    d, flag, p, secure, exp, name, value = line.split('\t')[:7]
```

Expiry is **silent**: you get zero items, not an exception. Make the script exit non-zero when nothing was captured so the scheduler notices.

## Also worth doing

Abort `image` / `font` / `media` in `page.route`: faster, and fewer chances to trip bot detection. The data you want travels over XHR.

The pattern generalises to any site whose page issues a signed API call: **don't reverse the signature, borrow the page's hands.**
