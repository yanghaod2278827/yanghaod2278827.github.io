---
title: Where a static site's data comes from
slug: static-site-data-pipeline
date: 2026-11-20
tags: ["Hugo", "Automation", "Blogging"]
categories: ["Meta"]
cover:
  image: /images/covers/en/static-site-data-pipeline.png
  hidden: true
  alt: ""
  caption: ""
summary: None of the numbers on this site are typed in by hand — three scrapers, two local scheduled tasks, and one feedback loop that had to be closed before it ate itself.
---

This continues [the post about how the site is built](/en/posts/2026/10/how-this-site-is-built/). That one said the numbers are produced by scripts; this one takes the pipeline apart: where data comes from, when it is fetched, and what happens when a fetch fails.

## Three kinds of data, three levels of pain

**GitHub (easy).** Stars and project cards come from the GitHub API. The only wrinkle is that `api.github.com` is TLS-intercepted on this machine and Python's certificate bundle rejects it, so the script falls back to the `gh` CLI when urllib raises a certificate error.

**Douban (medium, needs a cookie).** Watch history is scraped from `movie.douban.com/people/<id>/collect` with a logged-in session. Two traps:

- Douban is touchy about rapid pagination — I have seen it return a login shell and zero items. The scraper is throttled to at most once every four hours.
- Posters **cannot be hot-linked**: `img*.doubanio.com` answers `418 I'm a teapot` directly, and with a referer it returns about 1 KB of anti-leech HTML. The site uses monogram tiles instead of posters.

**Activity (the annoying one).** Douban status, GitHub events and Bilibili uploads have no RSS, so a self-hosted [RSSHub](https://docs.rsshub.dev) (one Docker container on `127.0.0.1:1200`) turns them into JSON. The public instance answers 403, so self-hosting is not optional.

## When it is fetched

The site is static, and it does **not** scrape at build time — that would make every deploy slow and let someone else's outage break the build. Instead, data lands on this machine first and is committed:

```
local scheduled task ──scrape──► data/*.json ──commit only if changed──► GitHub ──push──► deploy
```

Two tasks: the activity feed every two hours, Douban watch history once a day (with that four-hour throttle). Both commit only when the content actually changed, so a higher frequency never produces empty commits.

## The feedback loop

The first version produced a strange artefact: the activity timeline started listing "pushed to `yanghaod2278827.github.io`", and the entries kept multiplying.

The cause is obvious in hindsight: every sync run that commits `data/activity.json` is a push; the GitHub activity feed treats that push as new activity; the next run sees "new data" and commits again — **once every two hours, forever**.

The fix is to exclude this site's own repository from the GitHub source. Self-observing systems invite this kind of loop; it rarely shows up while you are writing the code, only after it runs.

## When a fetch fails

Every script keeps the previous JSON, prints a warning and exits successfully. The build carries on and the numbers simply stay one round stale — much better than failing a deploy over a scrape that was only a convenience, since the real data pipeline here runs locally, not in CI.

Cookies expire; Douban then returns a login page and the log says `no items scraped`. Grab a fresh cookie from the browser, drop it in a local file, and nothing else changes.

## The search index is built too

Search has no backend: the build emits an extra `index.json` (title, summary, first 800 characters of text) and `/search/` filters it in the browser. For a few dozen posts that index is a few dozen kilobytes — not worth running Elasticsearch.

---

The design in one line: **scraping is offline, commits only happen on change, and the build stays purely static.** Any one of the three can fail without dragging the other two down.
