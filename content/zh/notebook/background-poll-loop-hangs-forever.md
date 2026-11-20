---
title: 后台轮询会安静地空转两个多小时
slug: background-poll-loop-hangs-forever
date: 2026-11-20
tags: ["Shell", "后台任务", "踩坑"]
summary: 用 until/while + sleep 在后台等一个产物，之后的任何一次改名都会让条件永远不成立；进程不报错、不吃 CPU，只有主动枚举命令行才能发现。
---

仿真跑了四十分钟，我起了一个后台命令等它的结果文件出来：

```bash
until grep -q '"phase": "p26"' out/summary.json; do sleep 30; done
```

后来我把输出里的标签从 `p20/p26` 改成了 `pa/pb`。**条件从此永远不成立**——那个 bash 进程每 30 秒醒一次、什么也不做、继续睡，持续了 **2 小时 45 分钟**，还带着三个子进程。

## 为什么没被发现

三个原因叠在一起：

1. **不报错。** 它不是失败，是"还没好"，而"还没好"是这行命令本来就要表达的状态。
2. **不吃 CPU。** `sleep` 时 CPU 占用接近 0，任何看负载的监控都显示一切正常。
3. **完成通知认错了对象。** 后台任务超时转后台后有自己的 task ID，我按"收到完成通知 = 那个任务结束了"推断，漏掉的恰是没发通知的那一个。

## 三个修法，缺一不可

**一、一律套超时。** 无论是 `timeout 3600 bash -c '...'`，还是在循环里加最大次数：

```bash
i=0
until grep -q '"phase": "pa"' out/summary.json; do
  sleep 30
  i=$((i+1))
  [ $i -ge 120 ] && { echo "TIMEOUT after 1h" >&2; exit 1; }
done
```

`timeout` 只保证会结束，不保证你知道为什么没等到——所以配一条明确的超时消息。

**二、轮询条件不要依赖文件名或标签。** 这类"名字"是你会随手改的东西，每改一次都可能把条件悄悄变成永假。更稳的判据是**进程还在不在**，或**产物 mtime 有没有前进**：

```bash
until [ -n "$(pgrep -x lmp)" ] || [ "$(stat -c %Y out/summary.json 2>/dev/null)" -gt "$start" ]; do
  sleep 30
done
```

进程没了 = 跑完了（无论成败，成败再去看日志）；文件变新 = 有进展。两者都不依赖具体内容写的是什么。

**三、收尾时主动查残留。** 不要相信"我起了几个后台任务就结束了几个"。Windows 下按命令行筛：

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.Name -eq 'bash.exe' -and $_.CommandLine -match 'until|while' } |
  Select-Object ProcessId, CreationDate, CommandLine
```

Unix 同理：`ps -eo pid,etime,cmd | grep -E 'until|while'`。

## 同一类泄漏

长跑的"服务"和轮询是一回事：求解器常驻会一直占着许可证席位，浏览器调试实例会一直占着端口。任务收尾时把它们一起停掉，否则下一次运行会撞上"资源被占用"这种更难查的问题。

## 判据

> 后台任务只有在**你能说出它什么时候一定会结束**时才算安全。

"条件成立就结束"不是答案，因为条件可能永远不成立。加上限、换成不依赖命名的判据、收尾枚举进程——三件事都做了，才叫挂好了。
