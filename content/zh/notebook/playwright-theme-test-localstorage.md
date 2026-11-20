---
title: 用 Playwright 测主题切换，别在 init script 里清 localStorage
slug: playwright-theme-test-localstorage
date: 2026-11-20
tags: ["Playwright", "测试", "前端"]
summary: add_init_script 每次导航都会执行，会把「刷新后主题仍然保持」的断言误判成失效。
---

站点加了昼夜切换（主题存在 localStorage），想用 Playwright 验证「切到暗色 → 刷新 → 仍然是暗色」。第一版测试结果报「刷新后主题丢失」，但手动在浏览器里操作明明好好的。

## 根因

测试里为了「每次从干净状态开始」，写了这么一句：

```python
page.add_init_script("try{localStorage.removeItem('theme')}catch(e){}")
```

`add_init_script` 的语义是**每个 document 加载前都执行一次**，不是只执行一次。于是：

1. 点击切换 → 写入 `localStorage.theme = 'dark'`
2. `page.reload()` → 新的 document 加载前，init script 把它删了
3. 页面按 `prefers-color-scheme` 初始化 → 回到浅色

测试失败，站点其实没问题。

## 修法

分两个 context，别混用：

- **要「干净起点」**：新建 context（`browser.new_context()`），天然没有 localStorage，不需要 init script
- **要「验证持久化」**：同一 context 里 reload / 站内跳转，什么 init script 都别加

```python
ctx = browser.new_context(color_scheme='light')
page = ctx.new_page()
page.goto('/')
page.click('.theme-toggle')
page.wait_for_timeout(200)
assert page.evaluate("document.documentElement.classList.contains('dark')")
page.reload()
assert page.evaluate("document.documentElement.classList.contains('dark')")  # 这里才是真验证
```

## 通用教训

`add_init_script` 和 `evaluate` 的区别不是「执行时机早晚」，而是**执行次数**：前者每导航一次跑一次，后者只跑一次。任何「状态应当跨导航保持」的断言，都不能在前者存在的前提下做。
