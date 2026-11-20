---
title: Your Claude Code token bill — ccusage can overcount 2.4×
slug: token-bill-ccusage-double-counts
date: 2026-11-20
tags: ["Claude Code", "Usage Stats", "Cost"]
summary: Claude Code writes one response as several transcript lines (one per content block) with identical usage fields. ccusage dedupes on message.id + requestId, requestId is absent, so tokens inflate roughly 2.4× and the USD column uses prices that do not apply to third-party providers.
---

To find out what I actually spend in Claude Code, I installed `ccusage` and pointed it at the local transcripts. The output was tidy, professional and **wrong**: 30.7M tokens for one day, versus 13.2M after deduplicating by `message.id` — **2.4× inflated**.

## Cause: one response, many lines

Transcripts (`~/.claude/projects/**/*.jsonl`) are not one line per message. **A single response is split by content block** — one line starting with `thinking`, one with `text`, one with `tool_use` — and **every one of those lines carries the identical `usage` object** (`cache_read`, `input`, `output` all equal). They are copies of one request, not several requests.

`ccusage` dedupes on `message.id + requestId`, and transcripts **do not contain `requestId`** — so dedupe never fires and each copy is billed separately.

Check it yourself: in `ccusage session --json`, the same response appears twice in the raw entries, timestamps 96 ms apart.

## Second problem: dollar prices

The USD column uses LiteLLM's standard rate card. That is fine for OpenAI-style providers and wrong for third-party models priced in another currency. Treat the money column as a trend indicator, not a bill.

## Doing the arithmetic yourself

1. **Deduplicate by `message.id`** — count each id once, regardless of how many content-block lines it produced.
2. **Classify each request by timestamp** — many providers surcharge certain hours.
3. **Apply the provider's official rate card** — read it from the provider's docs, never from constants copied out of someone's open-source repo.

Emit machine-readable JSON (`ensure_ascii=True`, pure ASCII) so a shell prompt can parse it without hitting Windows code-page problems, and do the formatting on the shell side.

## Performance degrades with data volume

The first version scanned every transcript on every run: 0.5 s when small, 17–21 s once the corpus reached 2.78 GB across 549 files — unusable from a prompt that refreshes constantly.

The fix is an **mtime pre-filter**: for a given day, only scan files written during that period. That needs one invariant verified first — transcript timestamps are UTC while mtime is local, so a record dated to a UTC day must have been written after 08:00 local, hence its mtime is at or after local midnight. Verify by byte-comparing pre-filtered output against the full scan for two frozen historical dates. The day view then drops from 17–21 s to 1.5 s.

## Traps worth naming

- **`--offline` is not optional**: without it the tool re-fetches its price table every run — 16.3 s versus 0.25 s, a 60× difference.
- **`--compact` hides the cache column**, and cache reads often exceed 90% of the total — do not add it when you care about volume.
- **Do not detect secrets by "looks like a long random string"** — transcripts are full of hashes and URLs; match exact credential prefixes instead.

## Rule of thumb

> Before trusting a tool's money numbers, look at what it deduplicates on — and confirm that field exists in your data.

If it does not, the totals are just duplicated lines added together.
