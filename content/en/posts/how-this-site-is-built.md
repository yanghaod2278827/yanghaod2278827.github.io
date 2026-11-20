---
title: How this site is built
slug: how-this-site-is-built
date: 2026-10-30
tags: ["Hugo", "Blogging"]
categories: ["Meta"]
cover:
  image: /images/covers/en/how-this-site-is-built.png
  hidden: true   # a square design cover makes a poor PaperMod banner; kept for og:image
  alt: ""
  caption: ""
summary: Hugo plus PaperMod. Every number is fetched by a script, and the site documents itself.
---

Six kinds of content live here: a **blog**, **notes split by topic**, **films**, an **activity timeline**, **publications**, and **project cards**. All built with Hugo on a lightly customised PaperMod theme.

## Why Hugo

I looked at [DIYgod](https://diygod.cc)'s personal site (the author of RSSHub and xLog) as a reference. Three structural ideas were worth borrowing: split content into topic collections, let scripts generate the numbers, and keep the theme source in the repo instead of installing it as a dependency. His site runs on something other than Jekyll these days, but those choices do not depend on the framework.

I avoided anything that needs a runtime: Hugo is a single binary, a one-character edit refreshes in under a second, and its `data/` directory happily holds scraped JSON.

## The theme: PaperMod

Until November 2026 the site used hand-written templates (dashed grid background, stacked dashed cards). It looked good but every feature had to be built by hand. Switching to [PaperMod](https://github.com/adityatelange/hugo-PaperMod) bought search, archives grouped by year and month, a table of contents, related posts and dark mode.

The theme is **vendored into the repo** (`themes/PaperMod/`, not a submodule): CI needs no extra configuration and upgrading means replacing one directory. The trade-off is a more document-like card style, so four pages stay custom — films, activity, publications and projects — with a single `custom.css`.

## Where the numbers come from

None of them are typed in by hand:

| Number | Source |
|:--|:--|
| Post/note counts, category and tag counts | Hugo, at build time |
| Repo stars, project cards | `scripts/fetch_data.py` against the GitHub API |
| Films watched, short reviews | `scripts/fetch_douban.py` (needs a cookie) |
| Activity timeline | `scripts/fetch_activity.py` against a local RSSHub (Douban status, GitHub, Bilibili) plus `fetch_douyin.py` for Douyin |
| Publications | `scripts/fetch_orcid.py` against the public ORCID record |

The scraped JSON is committed, so the build reads it directly — **a failed fetch never breaks the build**, the numbers just stay at their last value.

## Content layout

```
content/zh/     Chinese (site root)
content/en/     English (/en/ prefix)
  ├── posts/      blog
  ├── notebook/   technical notes
  ├── movies/     films
  ├── activity/   activity timeline
  ├── publications/  publications
  └── projects/   project cards
```

Each is a Hugo section with its own `_index.md`; translations pair up by matching path and slug.

## Search and archives

Search is entirely client-side: the build also emits an `index.json`, and `/search/` filters it with fuse.js. Chinese works by substring, no backend involved.

## Deployment

Push to GitHub; Actions runs `hugo --minify --gc` and publishes to Pages. Freshness of the data comes from local scheduled tasks that scrape, commit only when something changed, and push — which triggers a deploy.

---

This page is its own documentation: to change something, find the corresponding file in the repo.
