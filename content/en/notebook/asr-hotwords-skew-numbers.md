---
title: ASR hotwords skew numbers — 80 and 20 are one context away
slug: asr-hotwords-skew-numbers
date: 2026-11-20
tags: ["ASR", "Audio", "Verification"]
summary: Hotword-biased transcription reads fluently and never errors, yet amounts, years and quotas get pulled toward neighbouring entries in the hotword list. Any number you plan to act on needs a no-hotword rerun plus a second, structurally different engine.
---

I transcribed a talk with a local ASR model and a domain hotword list. The numbers came out perfectly readable — grammatical, in context, plausible — and wrong. Wrong enough that I concluded the speaker's own figures contradicted each other.

The recognition did not fail. It succeeded in the wrong direction.

## Symptom

With "eighty" in the hotword list, the word actually spoken — "twenty" — was transcribed as eighty. Both are close in sound; under context bias, the hotword prior is enough to flip the decision.

What makes this nasty is the total absence of a signal:

- no error, no warning, nothing in the log;
- the output reads **better** than reality — "eighty" plus the rest of the sentence produced a coherent, self-consistent, completely wrong set of numbers;
- small models show it most, larger ones are not immune.

## Why fluent output is the bad case

The usual silent failure loses information. This one corrupts it. You act on a conclusion that looks reasoned, which is far harder to catch than garbled text — garbled text sends you looking, a fluent mistake gets adopted.

## The check

For any number that feeds a decision — money, duration, cohort year, quota, date — do three passes:

```bash
# 1. locate the passage with word-level timestamps
grep -n "eighty" transcript.srt

# 2. cut 15–45 s around it: enough context, no extra noise
ffmpeg -ss 00:12:30 -to 00:12:58 -i audio.wav clip.wav

# 3. rerun the same model with hotwords removed
python transcribe.py clip.wav --no-hotwords
```

Then run the same clip through a **structurally different** engine — Qwen3-ASR versus SenseVoice, or Paraformer. Different architecture and decoding, not the same model at another size.

**Trust only what both engines agree on.** When they disagree, mark the number "unresolved" instead of picking the one you like better — they can both be wrong in different ways, but at least you now know this is not a fact yet.

## One layer further

Even unanimous agreement only means the transcript is right. The number is still something someone said out loud, with slips of the tongue, later corrections and unspoken qualifiers. For decisions, go to the written source; ASR's job is to tell you **which sentence to read**.

## Rule of thumb

> A number endorsed by one engine has not been verified.

Hotwords are not free accuracy — you buy recognition rate by biasing the decoder toward a list. Whenever that list contains numbers, budget for the extra pass.
