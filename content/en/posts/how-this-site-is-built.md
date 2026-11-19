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

Four kinds of content live here: a **blog**, **notes split by topic**, **movies and a social timeline**, and **project cards**. All built with Hugo on a lightly customised PaperMod theme.

## Why Hugo

I looked at Guofei's personal site as a reference. He uses Jekyll, and three structural ideas were worth borrowing: split content into topic collections, let scripts generate the numbers, and keep the theme in the repo instead of installing it as a dependency.

Jekyll builds are slow and local preview needs Ruby. Hugo is a single binary, a one-character edit refreshes in under a second, and its `data/` directory happily holds scraped JSON.

## The theme: PaperMod

Until November 2026 the site used hand-written templates (dashed grid background, stacked dashed cards). It looked good but every feature had to be built by hand. Switching to [PaperMod](https://github.com/adityatelange/hugo-PaperMod) bought search, archives grouped by year and month, a table of contents, related posts and dark mode.

The theme is **vendored into the repo** (`themes/PaperMod/`, not a submodule): CI needs no extra configuration and upgrading means replacing one directory. The trade-off is a more document-like card style, so three pages stay custom — movies, activity and projects — with a small `custom.css`.

## Where the numbers come from

None of them are typed in by hand:

| Number | Source |
|:--|:--|
| Post/note counts, category and tag counts | Hugo, at build time |
| Repo stars, project cards | `scripts/fetch_data.py` against the GitHub API |
| Films watched, short reviews | `scripts/fetch_douban.py` (needs a cookie) |
| Activity timeline | `scripts/fetch_activity.py` against a local RSSHub (Douban status, GitHub, Bilibili) |

The scraped JSON is committed, so the build reads it directly — **a failed fetch never breaks the build**, the numbers just stay at their last value.

## Content layout

```
content/zh/     Chinese (site root)
content/en/     English (/en/ prefix)
  ├── posts/      blog
  ├── reading/    reading notes (sorted by title)
  ├── notebook/   technical notes
  ├── movies/     films
  ├── activity/   activity timeline
  └── projects/   project cards
```

Each is a Hugo section with its own `_index.md`; translations pair up by matching path and slug.

## Search and archives

Search is entirely client-side: the build also emits an `index.json`, and `/search/` filters it with fuse.js. Chinese works by substring, no backend involved.

## Deployment

Push to GitHub; Actions runs `hugo --minify --gc` and publishes to Pages. Freshness of the data comes from local scheduled tasks that scrape, commit only when something changed, and push — which triggers a deploy.

---

This page is its own documentation: to change something, find the corresponding file in the repo.
