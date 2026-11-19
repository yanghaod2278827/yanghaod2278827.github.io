---
title: 这个站点是怎么搭的
slug: how-this-site-is-built
date: 2026-10-30
tags: ["Hugo", "建站"]
categories: ["建站"]
cover:
  image: /images/covers/zh/how-this-site-is-built.png
  hidden: true   # 方形设计封面不适合当 PaperMod 横幅；保留给 og:image
  alt: ""
  caption: ""
summary: Hugo + PaperMod，数据全部由脚本抓，站点本身就是仓库里的一份文档。
---

这个站点有四类内容：**博客**、**按主题拆的笔记**、**观影与动态**、**项目卡片**。全部用 Hugo 构建，主题是自己改过的 PaperMod。

## 为什么是 Hugo

我参考了郭飞的个人站——他用 Jekyll，结构上有三件事值得抄：把内容按主题拆成自定义集合、把页面上的数字交给脚本生成、主题直接放在仓库里而不是装成依赖。

Jekyll 我没选，原因是构建慢、本地预览要等 Ruby 环境。Hugo 是单个 exe，改一个字秒级刷新，`data/` 目录也能直接放抓来的 JSON。

## 主题：PaperMod

2026-11 之前我用的是自己写的模板（方格虚线背景、双层虚线卡片），好看但功能要自己补。后来换成 [PaperMod](https://github.com/adityatelange/hugo-PaperMod)，换来现成的搜索、归档（年 → 月分组）、文章目录、相关文章和暗色模式。

主题是**直接放进仓库**的（`themes/PaperMod/`，不是 submodule）——CI 不用额外配置，升级就是重新下载覆盖一个目录。代价是主题自带的卡片风格更"文档站"，我保留了三处自己写的页面（观影 / 动态 / 项目）和一个小的 `custom.css` 来放它们。

## 数据是怎么来的

页面上的数字没有一个是我手填的：

| 数字 | 来源 |
|:--|:--|
| 文章数、笔记数、分类标签计数 | Hugo 构建时自己数 |
| 仓库 stars、项目卡片 | `scripts/fetch_data.py` 调 GitHub API |
| 观影数、短评 | `scripts/fetch_douban.py` 抓豆瓣（带 cookie） |
| 动态时间线 | `scripts/fetch_activity.py` 抓本机自建的 RSSHub（豆瓣广播 / GitHub / B站） |

抓下来的 JSON 提交进仓库，站点构建时直接读——**抓取失败也不会让构建挂掉**，只是数字停留在上一次。

## 内容结构

```
content/zh/     中文（根路径）
content/en/     英文（/en/ 前缀）
  ├── posts/      博客
  ├── reading/    读书笔记（按书名排序）
  ├── notebook/   技术笔记
  ├── movies/     观影
  ├── activity/   动态时间线
  └── projects/   项目卡片
```

每个 section 都有自己的 `_index.md`，中英两份靠「相同路径 + 相同 slug」对应。

## 搜索与归档

站内搜索是纯前端的：构建时多输出一份 `index.json`，`/search/` 用主题自带的 fuse.js 过滤，中文按子串匹配，不需要后端。

## 部署

推到 GitHub，Actions 自动 `hugo --minify --gc` 并发布到 Pages。数据的新鲜度靠本机计划任务：定时跑抓取脚本，有变化才 commit + push，从而触发一次部署。

---

这个页面本身就是一份文档：想改什么，去仓库里找对应的文件就行。
