---
title: Why portrait phone videos still lie down after conversion
slug: phone-video-rotation-and-verify
date: 2026-11-20
tags: ["ffmpeg", "Video", "Tools"]
categories: ["Tools"]
cover:
  image: /images/covers/en/phone-video-rotation-and-verify.png
  hidden: true
  alt: ""
  caption: ""
summary: Rotation lives in metadata, ffprobe may not report it, and a bare filter chain can silently ignore it — then you still have to prove the transcode did not damage anything.
---

A video shot in portrait plays upright, then comes out sideways after an ffmpeg transcode — or you add a rotation flag and it is still crooked. That is not an ffmpeg bug: **rotation is metadata**, and different tools treat it differently.

## Where rotation actually lives

MP4 stores rotation in the track header matrix (`rotate` / `displaymatrix`); the pixels never move. Consequences:

- Players read the metadata and show it upright
- `ffprobe` may **not print it by default** (especially older builds), so you conclude the file was already upright
- Some pipelines keep it, some drop it, and some **keep it *and* rotate the pixels** — the result looks like it was rotated twice, i.e. not at all

The only real check is to look at the output. Do not trust what `ffprobe` says about orientation.

## Bake the rotation, once

Do not rely on a flag being interpreted. Bake it into pixels and clear the metadata:

```bash
ffprobe -v error -show_streams -select_streams v:0 input.mp4 | grep -i rotation
ffmpeg -i input.mp4 -vf "transpose=1" -metadata:s:v rotate=0 -c:a copy out.mp4
```

`transpose=1` is 90° clockwise, `2` counter-clockwise; `0`/`3` combine with `hflip`/`vflip`. The `-metadata:s:v rotate=0` matters: leave it in place and some players apply both the metadata and the baked rotation.

## Prove the transcode did not damage anything

This is the step most people skip. After converting dozens of files, inspecting the first and last one and treating "no errors" as success is a proxy metric, not verification.

| Check | How | Threshold |
|:--|:--|:--|
| Picture | SSIM on the same frame from both files | > 0.98 (NVENC is lossy; 1.0 is unrealistic) |
| Duration | `ffprobe` duration on both sides | difference < 1 s |
| Audio | stream duration and peak level | same duration, not silent |
| Orientation | extract a frame and look | subject upright |

SSIM comes free with ffmpeg:

```bash
ffmpeg -i old.mp4 -i new.mp4 -lavfi "[0:v][1:v]ssim" -f null - 2>&1 | grep SSIM
```

Two more practical traps:

- **Two ffmpeg installations.** The first one on `PATH` may be the build shipped with LAMMPS (4.0.2) which has **no NVENC** — `-c:v hevc_nvenc` fails outright. Use the full path or fix the PATH order.
- **Never delete the source while encoding.** Write to a fresh directory, verify, then move originals to the recycle bin and confirm they are actually there. "I deleted it" and "it is deleted" are different claims.

## For batches

Scan → encode (2–3 concurrent NVENC streams; the encode chip, not the CUDA cores, is the limit) → per-file SSIM + duration + audio check → report with concrete numbers → human confirmation before archiving the originals. A report that only says "success" is not a report.
