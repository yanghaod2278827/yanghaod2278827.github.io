---
title: RSSHub 的豆瓣广播路由只认数字 uid
slug: rsshub-douban-numeric-uid
date: 2026-11-20
tags: ["RSSHub", "豆瓣", "抓取"]
summary: 字母型豆瓣 id 在该路由上会 404，表现为 503；数字 id 藏在头像链接里。
---

自建 RSSHub 想订阅自己的豆瓣广播：

```
http://127.0.0.1:1200/douban/people/d2278827/status
```

返回 **503**，容器日志里是 `FetchError: 404`——上游地址是 `m.douban.com/rexxar/api/v2/status/user_timeline/d2278827`。

## 根因

这个路由的内部实现只接受**整数型用户 id**，字母型 id（`d2278827` 这种自定义域名）会直接 404。文档里写了「目前只支持整数型 id」，但报错表现是 503，很容易以为是 RSSHub 挂了。

## 数字 id 从哪来

豆瓣个人页的头像链接里带着：

```
https://img9.doubanio.com/icon/ul122411510-1.jpg
                              ^^^^^^^^^ 这就是数字 id
```

```python
import re, urllib.request
h = urllib.request.urlopen('https://www.douban.com/people/<字母id>/').read().decode()
print(set(re.findall(r'/icon/u[l]?(\d+)-', h)))   # {'122411510'}
```

换成 `/douban/people/122411510/status` 就能出数据了。

## 顺带两个坑

- **「看过 + 短评」的 `interests` 路由已从主库删除**（`lib/routes/douban/people/` 只剩 `status.ts` / `wish.ts`），想看观影记录得自己抓 collect 页
- 加 `?format=json&limit=N` 直接拿 JSON，返回结构是 `{items:[{title, content_html, url, date_published}]}`，其中 `date_published` 是 **UTC**，落盘前记得转本地时区

判据：路由报 503 但日志里是上游 404，先怀疑参数格式，别怀疑服务。
