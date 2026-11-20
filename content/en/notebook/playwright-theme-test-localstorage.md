---
title: Testing theme persistence? Don't clear localStorage in an init script
slug: playwright-theme-test-localstorage
date: 2026-11-20
tags: ["Playwright", "Testing", "Frontend"]
---

The site has a light/dark toggle backed by localStorage. A Playwright test meant to verify "switch to dark → reload → still dark" reported that the theme was lost on reload — while doing it by hand worked fine.

## Cause

To start from a clean state the test did this:

```python
page.add_init_script("try{localStorage.removeItem('theme')}catch(e){}")
```

`add_init_script` runs **before every document load**, not once. So:

1. Click → `localStorage.theme = 'dark'`
2. `page.reload()` → before the new document initialises, the init script deletes the key
3. The page falls back to `prefers-color-scheme` → light

The test was broken, not the site.

## Fix

Use two contexts and never mix them:

- **Want a clean start**: create a fresh context (`browser.new_context()`) — it has no storage, no reset needed
- **Want to verify persistence**: reuse the same context across reloads and navigations, with no init script

```python
ctx = browser.new_context(color_scheme='light')
page = ctx.new_page()
page.goto('/')
page.click('.theme-toggle')
page.wait_for_timeout(200)
assert page.evaluate("document.documentElement.classList.contains('dark')")
page.reload()
assert page.evaluate("document.documentElement.classList.contains('dark')")  # the real check
```

## General lesson

The difference between `add_init_script` and `evaluate` is not *when* it runs but *how often* — once per navigation versus once total. Any assertion about state surviving a navigation is invalid while an init script is touching that state.
