---
title: RSSHub's Douban status route only accepts a numeric uid
slug: rsshub-douban-numeric-uid
date: 2026-11-20
tags: ["RSSHub", "Douban", "Scraping"]
summary: The route only accepts numeric ids; a vanity id 404s upstream and surfaces as 503. The numeric id hides in the avatar URL.
---

Subscribing to my own Douban status through a self-hosted RSSHub:

```
http://127.0.0.1:1200/douban/people/d2278827/status
```

Answered **503**, and the container log showed `FetchError: 404` against `m.douban.com/rexxar/api/v2/status/user_timeline/d2278827`.

## Cause

The route only accepts a **numeric** user id; a vanity id like `d2278827` 404s upstream. The docs say "only integer ids are supported", but surfacing as 503 makes it look like RSSHub itself is down.

## Where the numeric id lives

In the avatar URL on the profile page:

```
https://img9.doubanio.com/icon/ul122411510-1.jpg
                              ^^^^^^^^^ the numeric id
```

```python
import re, urllib.request
h = urllib.request.urlopen('https://www.douban.com/people/<vanity-id>/').read().decode()
print(set(re.findall(r'/icon/u[l]?(\d+)-', h)))   # {'122411510'}
```

`/douban/people/122411510/status` then returns items.

## Two related traps

- The **"watched + short review" `interests` route was removed** from the main repo (`lib/routes/douban/people/` has only `status.ts` and `wish.ts`), so watch history has to be scraped from the collect page yourself
- `?format=json&limit=N` returns `{items:[{title, content_html, url, date_published}]}`; `date_published` is **UTC**, convert before storing

Rule of thumb: when a route returns 503 but the log shows an upstream 404, suspect the parameters before the service.
