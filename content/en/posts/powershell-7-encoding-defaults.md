---
title: pwsh 7 changed the default encodings, not just the name
slug: powershell-7-encoding-defaults
date: 2026-11-25
tags: ["PowerShell", "Windows", "Encoding"]
categories: ["Windows"]
cover:
  image: /images/covers/en/powershell-7-encoding-defaults.png
  hidden: true
  alt: ""
  caption: ""
summary: The same script works under 5.1 and turns Chinese into question marks, UTF-16 logs and replacement characters under pwsh 7 — three defaults differ, and none of them raises an error.
---

## Symptom

The same script that behaves under `powershell.exe` (5.1) misbehaves under `pwsh.exe` (7): text piped into Python arrives as `????`, a redirected log is unreadable, and an old GBK file loads as a page of replacement characters.

Neither the script nor the command line changed. What changed is the **default encoding**.

## Three defaults, three different values

**One: `$OutputEncoding` decides what stdin is encoded as when piping to a native command.**

```powershell
# 5.1      → US-ASCII
# pwsh 7.7 → Unicode (UTF-8)
$OutputEncoding.EncodingName
```

Piping Chinese into a Python script that hex-dumps its stdin:

| Shell | Bytes received |
|:--|:--|
| 5.1 | `3f3f3f3f0d0a` — four `?`, the text is gone |
| pwsh 7.7 | `e6b58be8af95e4b8ade69687` — UTF-8, correct |

**Two: redirection to a file. 5.1 mis-decodes as GBK, then writes UTF-16.**

```powershell
python emit.py > out.txt
```

The resulting `out.txt`: 24 bytes starting with `FF FE` (UTF-16 LE with BOM) and mojibake inside under 5.1; 20 bytes of clean UTF-8 under pwsh 7.7, byte-identical to the program's output — native stdout goes straight to the file instead of passing through PowerShell's string layer.

**Three: capturing into a variable is broken in both shells.**

```powershell
$x = python emit.py        # garbled code points under 5.1 and 7 alike
```

One line before the capture fixes it in both (verified on each):

```powershell
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$x = python emit.py        # the six expected code points
```

## Why 5.1 writes UTF-16

Redirection in 5.1 is not a byte copy: the native command's output first enters PowerShell as a string (decoded once, using the console code page), then `Out-File` writes it out with its own default encoding — Unicode, i.e. UTF-16 LE. Chinese is mangled twice, once in each direction, which is why the file is both unreadable and UTF-16.

That is also why `$OutputEncoding` only covers **stdin piped to a native command** and says nothing about what a native command writes to stdout. In 5.1 they are two separate mechanisms, and neither covers for the other.

## Two directions for a fix

Fix the **shell defaults** — set `[Console]::OutputEncoding` (affects capture) and `$OutputEncoding` (affects stdin). Or fix the **call site** — replace `>` with `| Set-Content -Encoding utf8`, or have the program write its own file. Shell defaults are convenient interactively; call-site fixes survive changing machines or shells.

## Reading old GBK files: `-Encoding oem`

```powershell
Get-Content gbk.txt                  # 4 characters → 8 U+FFFD
Get-Content gbk.txt -Encoding oem    # correct
```

`Get-Content` in pwsh 7 assumes UTF-8, so `.bat` files and old logs fall apart. `-Encoding Default` does not save you either: with Windows 11's "Beta: Use Unicode UTF-8 for worldwide language support" enabled, `Default` *is* UTF-8. Write `oem` (code page 936) explicitly.

## Two syntax differences

- `-Encoding Byte` now fails with `'Byte' is not a supported encoding name`; use `-AsByteStream`.
- `Get-WmiObject` still exists in 7.7, but it is a compatibility function in `Microsoft.PowerShell.Management`, not a native cmdlet. New code should use `Get-CimInstance`.

## Rule

Faced with mojibake, ask **where this string is being decoded**: stdin handed to another process (`$OutputEncoding`), stdout written to a file (the redirection path), or the result PowerShell captured (`[Console]::OutputEncoding`). Three places, three switches — changing fonts, locales or reinstalling the OS helps with none of them.

The three habits: set `[Console]::OutputEncoding` before capturing native output; pass `-Encoding oem` for old GBK files; under 5.1, check that `$OutputEncoding` is not US-ASCII before feeding Chinese to a native command.
