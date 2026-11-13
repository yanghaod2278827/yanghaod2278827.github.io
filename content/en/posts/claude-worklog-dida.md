---
title: Turning a day's work into completed tasks, automatically
slug: claude-worklog-dida
date: 2026-11-13
tags: ["Claude Code", "Tools", "Automation"]
summary: Transcripts only contain conversations with Claude, but most of a day happens in Word, Origin, or an SEM. The missing half has to come from file timestamps.
---

After a while of using Claude Code, a need appeared: **knowing what I actually did today**. Not for reporting — because after a week I often can't remember which things moved.

The obvious approach is to read Claude Code's transcripts. But they only record my conversations with the model. And someone running experiments spends most of the day in Word revising a manuscript, in Origin drawing figures, in MATLAB tuning parameters. None of that leaves a single word in a transcript.

So [claude-worklog-dida](https://github.com/yanghaod2278827/claude-worklog-dida) uses two sources of evidence.

## Two sources of evidence

**One, transcripts**: every message I sent in today's Claude sessions. That's the "what I meant to do" signal.

**Two, file timestamps**: a scan of when files across the drives were modified or created. The first full scan covers about 1.4 million files in roughly 70 seconds, then narrows to a set of hot directories. That's the "what I actually did" signal.

Cross the two, and a task gets a plausible start and end time. File evidence is also tagged `[human]` or `[likely automated]` — files a script rewrote in bulk shouldn't count as work I did.

## The orchestrator makes no judgements

The pipeline runs hourly: scheduler → extract transcripts + scan files → one `claude -p` call → write back to Dida365's "completed" list → sync into that day's Obsidian diary block.

There's exactly one design rule: **the orchestrator does no judging; all of it is delegated to that single model call, with the rules living in `worklog_prompt.zh.md`.** How to categorise, how to set times, which items are the same task — all of that is the prompt's business. Change the behaviour by editing the prompt, not the code. I only understood this on the second version; the first one baked a pile of heuristics into Python, and every adjustment felt like surgery.

Reverse sync exists too: if I hand-write "checked the sapphire cutting-force data this morning" in the diary, the script fills that in as a completed task, instead of letting two records disagree with each other.

## The numbers are computed

In the Sunday weekly summary, every statistic — how many tasks were completed, the mix of categories, the longest stretch of continuous work — is computed by `weekly_extract.py` straight from the evidence. The model only writes prose. I learned this the hard way: asking a model to "summarise this week's data" produces numbers that look reasonable but don't match the records. The prompt now states explicitly: you may only cite numbers the script computed.

A run with activity costs about ¥0.15–0.5; a weekly summary about ¥0.23. Idle hours exit after the filesystem scan without calling the model.

## What it can't do

- It only covers work with **local traces**. Meetings, reading papers, phone calls are invisible unless I write them into the diary
- Windows only for the orchestration (PowerShell + Task Scheduler); the Python parts are portable
- Claude Code keeps transcripts for about 30 days, so longer gaps can't be backfilled

I marked it experimental when I published it. It solves my problem, and outside the combination of "Windows + Dida365 + Obsidian" it delivers less. But if you happen to live in that combination, ten minutes with `-DryRun` will tell you whether it fits.
