---
title: 不设 hasCJKLanguage，中文阅读时间永远是 1 分钟
slug: hugo-cjk-wordcount
date: 2026-11-20
tags: ["Hugo", "中文", "站点"]
summary: Hugo 默认按空格分词，1700 个中文字符只算 95 个词，于是阅读时间永远显示 1 分钟。一个配置项解决。
---

用 PaperMod 显示「约 N 分钟」，结果三篇文章全是「约 1 分钟」——包括一篇 1700 字的长文。

## 根因

Hugo 默认按**空白字符**分词。英文没问题，中文整段没有空格，于是：

- 1700 个中文字符 → `.WordCount` ≈ **95**
- 95 / 350 ≈ 0.27 → 四舍五入到 1 分钟

不只是阅读时间，`.Summary` 的自动截断、`related` 的相似度都会受影响。

## 修法

站点配置加一行：

```toml
hasCJKLanguage = true
```

打开后 Hugo 把中日韩字符按**字**计数，同一篇文章 `.WordCount` 变成约 1700，阅读时间恢复正常（中文按 350 字/分钟、英文 200 词/分钟，自己算一遍即可）。

```go
{{ $cpm := 200 }}
{{ if eq site.Language.Lang "zh" }}{{ $cpm = 350 }}{{ end }}
{{ $mins := math.Max 1 (math.Round (div (float .WordCount) $cpm)) }}
```

## 注意

这是一个**全站开关**：打开后所有页面的 `.WordCount` / `.Summary` 口径一起变。如果站上已有依赖「英文词数」的逻辑（比如按字数排序），要跟着核对一遍。

判据很简单：随便挑一篇中文字数已知的文章，看渲染出的数字是否和 `字数 ÷ 语速` 对得上。
