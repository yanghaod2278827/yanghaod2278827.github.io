---
title: TOML array tables quietly swallow the keys after them
slug: toml-array-table-swallows-keys
date: 2026-11-20
tags: ["Hugo", "TOML", "Config"]
---

I added `[[languages.zh.params.socialIcons]]` to a Hugo config and the homepage's about block disappeared — **no build error, no warning**, one section simply vanished.

## Symptom

```toml
[languages.zh.params]
  description = "notes and tools"
  [[languages.zh.params.socialIcons]]
    name = "github"
    url = "https://github.com/xxx"
  bio = """# Open source
Something about me."""
```

The template's `{{ with site.Params.bio }}` sees nil, so the whole block is skipped.

## Cause

Once a `[[array table]]` opens, **every bare key that follows belongs to that array element**, not to the parent table:

```toml
[[languages.zh.params.socialIcons]]
  name = "github"
bio = "…"     # actually socialIcons[0].bio
```

So `site.Params.bio` is nil and your text lives at `site.Params.socialIcons[0].bio`. `hugo config` confirms it: there is no `bio` among the top-level params.

## Fix

**Put array tables last** in any table that also has scalar keys:

```toml
[languages.zh.params]
  description = "…"
  bio = """…"""
  [[languages.zh.params.socialIcons]]
    name = "github"
```

The same applies to `[[menu.main]]`, `[[params.social]]`, anything `[[…]]`: after it, either write another array element or start a new table header — never a plain key of the parent.

## How to tell

When a config change makes part of a page disappear but the build is green, run `hugo config` and check whether the key still exists at the level you expect — before suspecting the template.
