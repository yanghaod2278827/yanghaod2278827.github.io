---
title: Python 抓 GitHub API，证书验证失败时退回 gh
slug: urllib-gh-api-fallback
date: 2026-11-13
tags: ["Python", "网络", "GitHub"]
---

这个站首页的 star 数是构建前跑脚本抓的。脚本第一版只用 `urllib.request`，本地一直正常，直到开了 FastGithub（DNS 劫持 + 本地反向代理，用来加速 GitHub）。

报错是 `CERTIFICATE_VERIFY_FAILED`。原因不复杂：FastGithub 在中间做了 TLS 终止，它用的证书装在 **Windows 证书存储**里。Go 写的程序（比如 `gh`）读的是系统存储，所以没事；Python 的 `urllib` 用的是自带的 `certifi` 证书包，里面没有这张证书。

## 不要用「关掉验证」解决

第一反应是 `ssl._create_unverified_context()`。能跑，但等于把整个站点的证书校验关掉了——以后真有人在中路换证书，脚本也不会知道。而且这个脚本要在 GitHub Actions 里跑，不能用本机特有的绕过方式。

## 退回 gh 的传输层

`gh api <url>` 输出就是 GitHub 的原始 JSON，用它当降级通道：

```python
def api(url):
    try:
        return _via_urllib(url)
    except Exception as e:
        if 'CERTIFICATE' in str(e) or 'SSL' in str(e):
            return _via_gh(url)   # subprocess: gh api <url>
        raise
```

只在**证书类**错误上降级，其他错误照常抛。这样 Actions 里走 urllib（快、无依赖），本地被代理 MITM 时走 `gh`（复用它的系统证书存储），两边都不用改代码。

一个附带的好处：`gh` 已经登录了，本地调试时不用担心匿名 API 的 60 次/小时限额。

## 抓不到数据时别让构建挂掉

数据脚本是构建流程的一环，网络抖动不该导致整站发布失败。所以抓取失败时**保留上一次的 JSON 直接退出**：

```python
except Exception as e:
    sys.exit('%s: %s (keeping previous data)' % (type(e).__name__, e))
```

页面上的数字会旧一天，但站点照常上线。对这类「数字好看但不是关键」的数据，宁可陈旧也不要中断。
