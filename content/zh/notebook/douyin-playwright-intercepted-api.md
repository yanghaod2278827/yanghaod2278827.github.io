---
title: 抖音抓取：让页面自己算签名，你只读它的响应
slug: douyin-playwright-intercepted-api
date: 2026-11-20
tags: ["抖音", "Playwright", "抓取"]
summary: 抖音接口带签名、RSSHub 路由又要 Chromium——换个思路：让页面自己发请求，我们只读响应。
---

想在「动态」里展示自己的抖音作品。RSSHub 有 `/douyin/user/:sec_uid` 路由，但用不了：

```ts
features: { requirePuppeteer: true, antiCrawler: true }
```

标准镜像里没有 Chromium；而且抖音网页端的接口带 `a_bogus` 之类的签名，自己拼请求基本没戏。

## 思路：不做客户端，做「旁观者」

用 Playwright 打开自己的主页，**让页面按照它自己的逻辑去发请求**，我们只挂一个 response 监听把结果截下来：

```python
captured = []
page.on('response', lambda r: captured.append(r.json())
        if '/aweme/v1/web/aweme/post/' in r.url else None)

page.route('**/*', lambda r: r.abort()
           if r.request.resource_type in ('image', 'font', 'media') else r.continue_())

page.goto('https://www.douyin.com/user/<sec_uid>', wait_until='domcontentloaded')
page.wait_for_timeout(8000)
```

签名由页面里的 JS 计算，cookie 由 context 提供，请求由页面发出——我们只解析 `aweme_list`。

## 关键前提：cookie

抖音的工作区和豆瓣不一样：

- 参数、路径都从 URL 里拿，`sec_uid` 就在主页地址上
- 但**必须带登录态 cookie**，否则页面加载了却不发作品请求（表现为监听 0 次命中）

我用的方式是浏览器扩展导出 Netscape 格式的 `cookies.txt`，脚本直接解析：

```python
for line in open(path):
    if line.startswith('#HttpOnly_'): line = line[len('#HttpOnly_'):]
    elif line.startswith('#'): continue
    d, flag, p, secure, exp, name, value = line.split('\t')[:7]
```

cookie 过期后的症状是**静默返回 0 条**，不是报错——所以脚本要在抓不到时以非零退出码结束，让上层任务能看见。

## 顺带：屏蔽图片和字体

`page.route` 把 `image` / `font` / `media` 全部 abort，既快又减少风控触发概率。作品数据在 XHR 里，跟这些资源无关。

这套思路适用于所有「页面自己会发一个带签名的接口」的站点：**别逆向签名，借页面的手**。
