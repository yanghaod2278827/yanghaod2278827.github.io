---
title: Why scheduled tasks pop up terminals at logon
slug: scheduled-task-popup-windows
date: 2026-11-25
tags: ["Windows", "Scheduled Tasks", "Terminal"]
categories: ["Windows"]
cover:
  image: /images/covers/en/scheduled-task-popup-windows.png
  hidden: true
  alt: ""
  caption: ""
summary: The task returns 0 and the work gets done — yet a dozen terminal windows flash up at logon. Whether a window appears is decided by the logon type and the default terminal, not by `-WindowStyle Hidden`.
---

## Symptom

Every reboot — or every logoff and logon — a dozen terminal windows open in a burst and close themselves a few seconds later. Task history says `LastTaskResult` 0 for all of them, and everything they were supposed to do did happen.

All of these tasks live under `\个人自动化\` (my personal automation folder) and most of them are triggered at logon. In other words: the work is fine, the *process* is just visible.

## Three conditions, all required

**The principal is Interactive.** `Get-ScheduledTask -TaskPath '\个人自动化\'` reports `Principal.LogonType` as `Interactive` for all 15 tasks — they run as the logged-in user in the visible session, so they are entitled to show a window.

**They all start at the same moment.** Logon triggers fire together right after logon. On Windows 11 the default terminal is Windows Terminal, and it **creates one window per console process** rather than grouping processes into one window. That is why you get fifteen windows, not one.

**`-WindowStyle Hidden` only governs the old host.** The parameter applies to conhost, the classic console host. Once Windows 11 moved the default host to Windows Terminal, it stopped affecting whether a window appears. The "Hidden" checkbox in Task Scheduler (`Settings.Hidden`) only hides the task from the list; it has nothing to do with windows either. Both express "the author wanted it hidden", never "it is hidden".

## Measure first

```powershell
Get-ScheduledTask -TaskPath '\个人自动化\' | ForEach-Object {
  $a   = $_.Actions | Select-Object -First 1
  $exe = Split-Path $a.Execute -Leaf
  '{0} | {1} | {2}' -f $_.TaskName, $_.Principal.LogonType, $exe
}
```

On this machine: 6 tasks run `python.exe`, 5 run `pythonw.exe`, 3 run `powershell.exe`, 1 runs `cmd.exe` — and every principal is `Interactive`.

To find out *who* opened the windows, use the Task Scheduler operational log (off by default):

```powershell
wevtutil sl Microsoft-Windows-TaskScheduler/Operational /e:true

$log = 'Microsoft-Windows-TaskScheduler/Operational'
Get-WinEvent -LogName $log -MaxEvents 800 |
  Where-Object Id -in 110,129 |
  Group-Object { $_.Properties[0].Value } |
  Sort-Object Count -Descending | Select-Object -First 5
```

Event 110 is "task triggered", 129 is "task process created", and `Properties[0]` is the task name. In my sample the top entries are `\NahimicTask32/64` — dynamic audio-driver tasks and perfectly normal noise that never shows a window. Split your own tasks from vendor tasks when grouping, or your handful will drown in the noise.

## Three fixes

**Python tasks: switch to `pythonw.exe`.** It is the console-less build in the same directory; the process never asks for a window. Smallest possible change — five of my frequent tasks now run this way.

**PowerShell or cmd tasks: wrap in `wscript`.** Three lines of VBScript:

```vbs
Set sh = CreateObject("WScript.Shell")
sh.Run "powershell.exe -NoProfile -File C:\path\to\task.ps1", 0, False
```

`0` hides the window, `False` means don't wait. Point the task action at `wscript.exe` running this file.

**Tasks with no desktop dependency: use an S4U principal.** S4U needs no stored password and does not load the user profile, so the task runs in a non-interactive session and has no window at all. The cost is no access to user-mapped drives or DPAPI-protected secrets — anything that needs browser cookies cannot be moved this way.

## Rule

Whether hiding worked is decided by two things only: **did a window appear**, and what `Principal.LogonType` / `Execute` say for that task. Under Windows 11's default terminal, `-WindowStyle Hidden` is not a usable signal — it says the author intended to hide, not that the window stayed hidden.
