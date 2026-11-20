---
title: 手机竖拍的视频，为什么转了还是躺着
slug: phone-video-rotation-and-verify
date: 2026-11-20
tags: ["ffmpeg", "视频", "工具"]
categories: ["工具"]
cover:
  image: /images/covers/zh/phone-video-rotation-and-verify.png
  hidden: true
  alt: ""
  caption: ""
summary: 旋转信息藏在元数据里，ffprobe 不一定报、不加滤镜也不生效；转完还得证明自己没转坏。
---

手机竖着拍的视频，在播放器里是正的，用 ffmpeg 一转码就躺下了——或者反过来，明明加了旋转参数，出来还是歪的。这不是 ffmpeg 的 bug，是**旋转信息存在元数据里**，而不同工具对它的态度不一样。

## 旋转到底存在哪

MP4 的旋转写在视频轨的 `tkhd` 矩阵里（`rotate` / `displaymatrix`），像素数据本身没动。于是：

- 播放器读元数据 → 显示正
- `ffprobe` 默认输出**可能不显示**这条信息（老版本尤其如此），你会以为视频本来就是正的
- 有些处理链路（重封装、滤镜、部分硬件编码器）**会保留它**，有些**会丢掉**，还有些**会既保留元数据又在画面里转一次**——结果就是"转了两次"，看着像没转

判据只有一个：转完用眼睛看，别信 `ffprobe` 的输出。

## 稳妥做法：先摊平，再按需转

不要指望"设个参数让它自己处理"。可靠的做法是把旋转一次性烘焙进像素：

```bash
# 1) 先看清真实状态：-show_streams 看 side_data 里的 rotation
ffprobe -v error -show_streams -select_streams v:0 input.mp4 | grep -i rotation

# 2) 把旋转烘焙进画面（transpose 后元数据清零）
ffmpeg -i input.mp4 -vf "transpose=1" -metadata:s:v rotate=0 -c:a copy out.mp4
```

`transpose=1` 是顺时针 90°，`2` 是逆时针，`0`/`3` 配 `-vf hflip`/`vflip`。关键是那句 `-metadata:s:v rotate=0`——不显式清零，某些播放器会把元数据和画面叠加，变成转了两次。

## 转完怎么证明没转坏

这一步最容易被跳过。批量转了几十个视频，肉眼只看头尾几条，剩下的靠"没报错"当成功——这是典型的代理指标。

可靠的验收是**逐条比对**：

| 检查 | 方法 | 判据 |
|:--|:--|:--|
| 画面 | 抽同一时间点的帧算 SSIM | > 0.98（NVENC 有损，别指望 1.0） |
| 时长 | 两侧 `ffprobe` 的 duration | 差值 < 1 秒 |
| 声音 | 音频流时长与峰值 | 时长一致，峰值不为静音 |
| 方向 | 抽帧看图 | 人像朝上，不是躺着的 |

SSIM 用 ffmpeg 内置滤镜就能算：

```bash
ffmpeg -i old.mp4 -i new.mp4 -lavfi "[0:v][1:v]ssim" -f null - 2>&1 | grep SSIM
```

另外两个实际的坑：

- **机器上装了两个 ffmpeg**：PATH 里先命中的那个可能是 LAMMPS 自带的 4.0.2，**没有 NVENC**，`-c:v hevc_nvenc` 直接报错。要么写全路径，要么先调 PATH 顺序
- **别边转边删源文件**。先转到一个新目录，校验通过后再把原件移进回收站，并确认回收站里确实多了这些文件——"我以为删了"和"确实删了"是两件事

## 批量的话

整套流程：扫描目录 → 逐个转（NVENC 并发 2–3 路，显存和编码芯片都撑得住）→ 逐条 SSIM + 时长 + 音频校验 → 出报告 → 人工确认后归档原件。报告里每条都要有具体数值，别只写"成功"。
