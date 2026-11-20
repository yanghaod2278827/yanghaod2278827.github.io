---
title: A background poll loop that spun for two hours and forty-five minutes
slug: background-poll-loop-hangs-forever
date: 2026-11-20
tags: ["Shell", "Background Jobs", "Pitfalls"]
summary: An until/while + sleep loop waiting on a product file never errors and never burns CPU — but one rename later the condition can never be true again, and only enumerating process command lines will show it.
---

A simulation takes forty minutes, so I launched a background command to wait for its output:

```bash
until grep -q '"phase": "p26"' out/summary.json; do sleep 30; done
```

Later I renamed the labels inside the output from `p20/p26` to `pa/pb`. **The condition could never be true again.** That bash process woke every 30 seconds, did nothing, and went back to sleep — for **two hours and forty-five minutes**, holding three child processes.

## Why nothing caught it

Three things lined up:

1. **It never errored.** This was not a failure; it was "not ready yet", which is exactly the state the command is designed to express.
2. **It used no CPU.** While sleeping it is effectively idle, so every load-based monitor says all is well.
3. **I credited the wrong completion notice.** Background tasks get their own task IDs, and I reasoned "a completion notice arrived, so the job finished" — the one I missed was the one that never sent a notice.

## Three fixes, all three required

**1. Always bound it.** Either wrap with `timeout 3600 bash -c '...'` or count iterations:

```bash
i=0
until grep -q '"phase": "pa"' out/summary.json; do
  sleep 30
  i=$((i+1))
  [ $i -ge 120 ] && { echo "TIMEOUT after 1h" >&2; exit 1; }
done
```

`timeout` guarantees it ends; it does not tell you why nothing arrived — so pair it with an explicit timeout message.

**2. Do not poll on names or labels.** Those are exactly the things you rename by hand, and every rename can silently turn the condition permanently false. Better signals: **is the process still there**, or **has the file's mtime moved**:

```bash
until [ -z "$(pgrep -x lmp)" ] || [ "$(stat -c %Y out/summary.json 2>/dev/null)" -gt "$start" ]; do
  sleep 30
done
```

Process gone means finished (success or failure — read the log to tell which); a newer mtime means progress. Neither depends on what the contents say.

**3. Sweep for leftovers when you wrap up.** Do not trust "I started N background jobs, so N are done". On Windows, filter by command line:

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.Name -eq 'bash.exe' -and $_.CommandLine -match 'until|while' } |
  Select-Object ProcessId, CreationDate, CommandLine
```

Same idea on Unix: `ps -eo pid,etime,cmd | grep -E 'until|while'`.

## The same leak in another costume

Long-running "services" leak the same way: a solver left resident holds a license seat, a debug browser holds a port. Stop them when the task ends, or the next run trips over "resource in use", which is much harder to diagnose than a hung loop.

## Rule of thumb

> A background job is only safe when you can state **when it must end**.

"Until the condition holds" is not an answer — conditions can be permanently false. A hard bound, a signal that does not depend on naming, and an end-of-task process sweep: all three, or it is not really launched safely.
