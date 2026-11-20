---
title: TOML 的数组表会偷偷吞掉后面的键
slug: toml-array-table-swallows-keys
date: 2026-11-20
tags: ["Hugo", "TOML", "配置"]
summary: TOML 的 [[数组表]] 一出现，后面的裸键就归它了——配置静默变空、页面少一块，构建却全绿。
---

给 Hugo 配首页社交图标，加完 `[[languages.zh.params.socialIcons]]` 之后，首页的「关于」块整个消失了——**构建零报错、零警告**，页面只是少了一块。

## 现象

配置大概长这样：

```toml
[languages.zh.params]
  description = "记录、笔记与一些小工具"
  [[languages.zh.params.socialIcons]]
    name = "github"
    url = "https://github.com/xxx"
  bio = """# 开源
这是自我介绍。"""
```

模板里 `{{ with site.Params.bio }}` 读到的是**空值**，于是整段 `with` 被跳过，页面静默少一块。

## 根因

TOML 的 `[[数组表]]` 一旦出现，**它后面的所有裸键都属于这个数组元素**，而不是回到父表：

```toml
[[languages.zh.params.socialIcons]]
  name = "github"
bio = "…"     # ← 这里其实写进了 socialIcons[0].bio
```

所以 `site.Params.bio` 是 nil，而 `site.Params.socialIcons[0].bio` 里躺着你写的那段文本。

可以用 `hugo config` 直接验证：顶层 `params` 里没有 `bio`，但把配置 dump 成 JSON 就能看到它挂在最后一个图标对象下面。

## 修法

**数组表一律放在该表所有普通键之后**：

```toml
[languages.zh.params]
  description = "…"
  bio = """…"""
  # 数组表放到最后
  [[languages.zh.params.socialIcons]]
    name = "github"
```

同类陷阱还有 `[[menu.main]]`、`[[params.social]]`——任何 `[[...]]` 之后，要么继续写数组元素，要么换新的表头，**别再写父表的普通键**。

## 判据

配置改完页面「少了一块」但构建全绿时，先 `hugo config` 看一眼那个键还在不在顶层，而不是去怀疑模板。
