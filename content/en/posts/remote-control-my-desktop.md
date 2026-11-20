---
title: Remote-controlling my own desktop from a phone
slug: remote-control-my-desktop
date: 2026-11-20
tags: ["Remote access", "Tailscale", "Tools"]
categories: ["Tools"]
cover:
  image: /images/covers/en/remote-control-my-desktop.png
  hidden: true
  alt: ""
  caption: ""
summary: ToDesk as the main channel, Tailscale plus SSH as the backup — the hard part is not installing software, it is keeping a closed laptop reachable.
---

The need is small: from the street, check whatever is running on the desktop and fire off a few commands. The conclusion after some trial and error is **two channels** — one for comfortable full-desktop use, one for getting in when the first one dies.

## Main channel: ToDesk

The subscription buys two features that matter here: a **privacy screen** (the physical monitor stays black while you are connected) and a **virtual display** (you still get a usable desktop with the lid closed). For "machine at home, person elsewhere", those are close to essential.

The weakness is dependence on the vendor's relay: a bad network means a dropped session.

## Backup: Tailscale + SSH

Tailscale puts the phone and the desktop on the same virtual network with stable IPs (`100.x.x.x`). Once the desktop runs an SSH server, any SSH client on the phone — Termius, for instance — can log in and run commands.

That path uses no third-party desktop protocol at all, needs almost no bandwidth, and the tunnel stays up in the background. The trade-off is no desktop, just a shell — which is all you need to check whether a job finished or restart a script.

Installing OpenSSH Server on Windows has its own traps:

1. It is an optional Windows feature and has to be installed first
2. The service does **not** start automatically — `Set-Service sshd -StartupType Automatic` and then `Start-Service sshd`
3. Port 22 has to be allowed through the firewall (the feature usually adds the rule; group policy can remove it)
4. By default only **key-based logins for the administrators group** are accepted; password auth is commented out in `sshd_config` and has to be enabled deliberately

## The actually hard part: keeping it awake

Installing the software is the easy bit. A laptop sleeps when you close the lid, and a sleeping machine answers nothing. What has to change is the whole power policy:

| Setting | Value | Why |
|:--|:--|:--|
| Lid close action | Do nothing | otherwise the link dies instantly |
| Sleep on AC | Never | |
| Turn off display | Never | unrelated on paper, but some drivers suspend along with it |
| Windows Update | Paused | a 3 a.m. reboot breaks everything |

There is also the opposite requirement: **do not let the machine sleep while work is running**. For long jobs — compiles, transcodes — a watchdog should hold the wake lock while something is busy, and release it after a quiet period.

The easy mistake here is treating *process existence* as *activity*. A machine with editors and terminals open has seven or eight resident processes; counting them means the wake lock is never released. Measure **deltas** instead: more than 0.45 s of CPU time, or more than 5 MB of I/O, in a 15-second window. CPU alone misses I/O-bound work like downloads, which then gets killed mid-transfer.

## The physical problem

Closing the lid puts the Wi-Fi antenna behind the chassis. Signal drops from full to two or three bars, and packet loss and latency to the router go up. No software fixes that — you either relocate the laptop or accept that the remote session gets choppy when the lid is shut.

Which is exactly why the second channel exists: when ToDesk drops, the lightweight SSH tunnel is often still alive.

---

Almost all of the complexity here is about *staying reachable*; installing the tools is a rounding error. Remote access is an operations problem, not a software one.
