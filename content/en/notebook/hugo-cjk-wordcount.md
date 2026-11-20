---
title: Without hasCJKLanguage, every Chinese post reads as 1 minute
slug: hugo-cjk-wordcount
date: 2026-11-20
tags: ["Hugo", "Chinese", "Site"]
---

PaperMod's "N min read" showed "1 min" for three posts in a row — including a 1700-character article.

## Cause

Hugo counts words by **whitespace**. Chinese has none between characters, so:

- 1700 Chinese characters → `.WordCount` ≈ **95**
- 95 / 350 ≈ 0.27 → rounds to 1 minute

It affects more than reading time: `.Summary` truncation and `related` scoring use the same number.

## Fix

One line in the site config:

```toml
hasCJKLanguage = true
```

Hugo then counts CJK characters individually; the same post reports ~1700, and reading time comes out right (350 characters/min for Chinese, 200 words/min for English):

```go
{{ $cpm := 200 }}
{{ if eq site.Language.Lang "zh" }}{{ $cpm = 350 }}{{ end }}
{{ $mins := math.Max 1 (math.Round (div (float .WordCount) $cpm)) }}
```

## Caveat

This is a **site-wide switch**: every page's `.WordCount` and `.Summary` change with it. If anything sorts or filters by word count, re-check it.

The check is trivial: pick a Chinese post whose length you know and see whether the rendered number matches length ÷ reading speed.
