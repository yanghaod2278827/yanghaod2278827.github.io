---
title: How this site is built
slug: how-this-site-is-built
date: 2026-10-30
tags: ["Hugo", "Blogging"]
summary: Hugo plus GitHub Actions. Every number on a page is produced by a script.
---

This site has three parts: a **blog**, **notes split by topic**, and a **data panel on the homepage**.

## Why Hugo

I looked at Guofei's personal site as a reference. He uses Jekyll, and three structural ideas were worth borrowing: split content into topic collections, let scripts generate the numbers on the page, and keep the theme in the repo instead of installing it as a dependency.

I didn't pick Jekyll because builds are slow and local preview needs a Ruby environment. Hugo is a single exe, a one-character change refreshes in under a second, and its `data/` directory is the same idea as Jekyll's `_data/` — the data-driven approach carries over unchanged.

## Where the numbers come from

Of the figures on the homepage:

- Article count, note count → Hugo counts them; nothing to maintain
- Star count → `scripts/fetch_data.py` calls the GitHub API and writes `data/github.json`
- Project cards → the same script writes `data/projects.json`

Templates read `site.Data.github.total_stars`, so none of these numbers are ever edited by hand.

## Content layout

```
content/
├── posts/      blog (sorted by date)
├── reading/    reading notes (sorted by book title)
├── notebook/   technical notes (by topic)
└── projects/   project cards (data from JSON)
```

Each is a Hugo section with its own `_index.md` and list page.

## Deployment

Push to GitHub. Actions runs `hugo --minify` and publishes to Pages. The whole thing is free.

---

This page is its own documentation: to change something, find the corresponding file in the repo.
