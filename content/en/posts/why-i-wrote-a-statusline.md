---
title: Why I wrote a status line for Claude Code
slug: why-i-wrote-a-statusline
date: 2026-10-30
tags: ["Claude Code", "Tools", "Cost"]
summary: The official cost figure was off from my real bill by 69×. That's not something I can ignore.
---

I run Claude Code against a third-party API. One day I glanced at its built-in cost counter and saw something absurd: the same session, reported as `$45.45`, while at the provider's published prices it cost `¥4.66`.

A factor of 69.

## Why the gap

Claude Code computes the cost field itself. It's accurate for the models it knows about — Anthropic's own. For third-party models it doesn't recognise, it applies Claude's prices. A model that costs a few yuan gets billed at flagship rates, and the difference is two orders of magnitude.

The nasty part is that **it doesn't fail loudly**. The number looks plausible. You won't doubt it until you reconcile against a real bill.

## A subtler bug

While writing this I dug through Claude Code's transcript files and found that it writes **one line per content block** for a single response — one for thinking, one for text, one for tool_use — and every one of those lines carries the *same* `usage` object.

Any tool that sums tokens line by line will overcount by roughly 2.4×. Several popular statistics tools step right into it.

## So I wrote this

[claude-statusline](https://github.com/yanghaod2278827/claude-statusline) does three things:

1. **Deduplicates by `message.id`** — one response counts once
2. **Prices each request at the rate in effect at the time** — a request at 09:59 and one at 10:01 are billed differently
3. **Moves the balance in the same frame as the spend**, instead of jumping every two minutes

It also handles peak/off-peak pricing, public holidays, and cache hit rate.

## One more thing

After finishing it I looked around and found that others had built similar tools, some more complete than mine. I don't regret it — **writing it was how I worked out why the numbers were wrong**, and that's worth more than one more tool.

If you're running Claude Code against a third-party API, do one thing before installing anything: find out what your provider actually charges. A surprising share of the price tables floating around are wrong.
