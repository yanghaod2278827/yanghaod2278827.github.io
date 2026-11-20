---
title: Claude Code 的 token 账单：ccusage 能多数 2.4 倍
slug: token-bill-ccusage-double-counts
date: 2026-11-20
tags: ["Claude Code", "用量统计", "成本"]
summary: Claude Code 把同一个 response 按 content block 分行写入转录，每行 usage 完全相同；ccusage 靠 requestId 去重而转录里没有这个字段，于是 token 虚高约 2.4 倍，美元价也套不上第三方 provider。
---

想搞清楚自己在 Claude Code 上到底花了多少钱，装了 `ccusage` 读本地转录。它给出的数字很整齐、很专业、也很**不对**：同一天的用量报 30.7M token，按 `message.id` 去重后只有 13.2M——**虚高 2.4 倍**。

## 根因：一个 response 被写成了多行

Claude Code 的转录（`~/.claude/projects/**/*.jsonl`）不是一条消息一行。**同一个 response 会按 content block 拆开**：第一个块是 `thinking`、`text` 还是 `tool_use`，就分成几行落盘。

关键在于：**这几行的 `usage` 字段完全相同**（`cache_read`、`input`、`output` 一模一样）。它们不是多次请求，是同一次请求的多份副本。

`ccusage` 的去重键是 `message.id + requestId`，而转录里**根本没有 `requestId` 字段**——去重逻辑失效，每一行都被当成一次独立请求计费。

验证方法很简单：`ccusage session --json` 里翻原始的 entries，同一个 response 会出现两条，时间戳只差 96 毫秒。

## 第二个坑：美元价

`ccusage` 的 USD 列用的是 LiteLLM 的标准价目表，对 OpenAI 那类 provider 是对的，对第三方 provider（按人民币计价的模型）就对不上。结论：**它的钱数不能当真，只看相对趋势**。

## 自己算：三步

1. **按 `message.id` 去重**——一个 id 只算一次，不再被 content block 行数影响；
2. **逐请求按时间戳判峰谷**——很多 provider 有工作日高峰加价；
3. **套官方价目表**——去官网核对，不要抄开源项目的常量。

写成脚本后，`--json` 输出纯 ASCII（避开 PowerShell 5.1 把 UTF-8 管道当 GBK 解码的坑），提示符侧再拼货币符号和排版。

## 性能：全量扫会随数据量退化

第一版每次运行都全量扫所有转录，数据量小时 0.5 秒，长到 2.78 GB（549 个文件）后要 17~21 秒——放到提示符里每次刷新都卡。

修法是 **mtime 预筛**：查询某一天时，只扫"那段时间被写过"的文件。这里要做一次交叉验证——转录里的时间是 UTC、mtime 是本地时间，得确认 UTC 当天的记录必然写于本地当天 08:00 之后（于是 mtime 一定 ≥ 本地当天 00:00）。用两个已经冻结的历史日期，把预筛结果与全量结果逐字节比对一致，才算放心。

当天查询因此从 17~21 秒降到 1.5 秒。

## 别犯的错

- **`--offline` 不是可选项**：不加时工具每次运行都联网重拉定价表，实测 16.3 秒 vs 0.25 秒，差 60 倍。
- **`--compact` 会隐藏 cache 列**，而 cache read 常占总量 90% 以上——看总量时别加这个参数。
- **别用"长度像不像密钥"去判断转录里有没有敏感内容**，转录里全是 hash 和 URL，会误杀；只认明确的密钥前缀形态。

## 判据

> 第三方工具给出的钱数，要先去它去重逻辑里看一眼：它靠什么字段去重？那个字段在你的数据里存在吗？

不存在的话，数字再整齐也只是把重复行加了起来。
