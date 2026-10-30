---
title: 这个站点是怎么搭的
slug: how-this-site-is-built
date: 2026-10-30
tags: ["Hugo", "建站"]
summary: Hugo + GitHub Actions，页面上的数字全部由脚本生成。
---

这个站点有三个部分：**博客**、**按主题拆的笔记**、**首页的数据面板**。

## 为什么是 Hugo

我参考了郭飞的个人站——他用 Jekyll，结构上做了三件事值得抄：把内容按主题拆成自定义集合、把页面上的数字交给脚本生成、主题直接放在仓库里而不是装成依赖。

Jekyll 我没选，原因是构建慢、本地预览要等 Ruby 环境。Hugo 是单个 exe，改一个字秒级刷新，而且它的 `data/` 目录和 Jekyll 的 `_data/` 是一回事——数据驱动的做法可以原样搬过来。

## 数据是怎么来的

首页那排数字里：

- 文章数、笔记数 → Hugo 自己数，不用维护
- Star 数 → `scripts/fetch_data.py` 调 GitHub API 生成 `data/github.json`
- 项目卡片 → 同一个脚本生成 `data/projects.json`

模板读 `site.Data.github.total_stars`，所以这些数字永远不需要手改。

## 内容结构

```
content/
├── posts/      博客（按日期）
├── reading/    读书笔记（按书名）
├── notebook/   技术笔记（按主题）
└── projects/   项目卡片（数据来自 JSON）
```

每一节都是一个 Hugo section，有自己的 `_index.md` 和列表页。

## 部署

推到 GitHub，Actions 自动 `hugo --minify` 并发布到 Pages。整个过程免费。

---

这个页面本身就是一份文档：想改什么，去仓库里找对应的文件就行。
