---
title: pwsh 7 换了默认编码，不只是换了名字
slug: powershell-7-encoding-defaults
date: 2026-11-25
tags: ["PowerShell", "Windows", "编码"]
categories: ["Windows"]
cover:
  image: /images/covers/zh/powershell-7-encoding-defaults.png
  hidden: true
  alt: ""
  caption: ""
summary: 同一个脚本在 5.1 里正常、到 pwsh 7 里中文变问号或文件变 UTF-16——三处默认值不同，而且没有一处会报错。
---

## 现象

同一段脚本，`powershell.exe`（5.1）里跑得好好的，换成 `pwsh.exe`（7）之后：管道喂给 Python 的中文变成 `????`，重定向出来的日志打开是乱码，读老 GBK 文件整段变成替换符。

脚本没改，命令行也没改。变的是**默认编码**。

## 三处默认值，各不相同

**一、`$OutputEncoding`：决定「喂给原生命令的 stdin」用什么编码。**

```powershell
# 5.1        → US-ASCII
# pwsh 7.7   → Unicode (UTF-8)
$OutputEncoding.EncodingName
```

实测把中文通过管道喂给一个只打印 stdin 字节的 Python 脚本：

| 壳 | 收到的字节 |
|:--|:--|
| 5.1 | `3f3f3f3f0d0a`（四个 `?`，中文全丢） |
| pwsh 7.7 | `e6b58be8af95e4b8ade69687`（UTF-8，正确） |

**二、重定向到文件：5.1 会先按 GBK 误解码，再写成 UTF-16。**

```powershell
python emit.py > out.txt
```

实测 `out.txt`：5.1 写出 24 字节、以 `FF FE` 开头（UTF-16 LE 带 BOM），内容是乱码；pwsh 7.7 写出 20 字节的纯 UTF-8，字节与程序输出一致——原生命令的 stdout 直接落到文件，没有经过 PowerShell 的字符串层。

**三、捕获到变量：两个壳都乱，必须显式指定控制台编码。**

```powershell
$x = python emit.py        # 5.1 和 7 都得到一串乱码码位
```

在捕获之前加一行就正确了（两个壳都实测有效）：

```powershell
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$x = python emit.py        # 测 → 试 → 中 → 文 → 输 → 出，六个码位正确
```

## 为什么 5.1 会写出 UTF-16

5.1 的重定向并不是「把字节倒进文件」：原生命令的输出先被当成字符串收进 PowerShell，按控制台代码页解码一次，再由 `Out-File` 用它自己的默认编码（Unicode，即 UTF-16 LE）写出。中文在两处各错一次，所以既乱码、又变成 UTF-16。

也正因为如此，`$OutputEncoding` 只管「管道喂给原生命令的 stdin」，**不管**原生命令写到 stdout 的内容——这两件事在 5.1 里是两套机制，谁也不能替谁兜底。

## 两种修复方向

一种是**改壳的默认**：设 `[Console]::OutputEncoding`（影响捕获）、`$OutputEncoding`（影响 stdin）。另一种是**改调用点**：不用 `>` 而用 `| Set-Content -Encoding utf8`，或者让脚本自己把结果写文件。改壳对交互式使用省事，改调用点对脚本可靠——同一段代码换台机器、换个壳仍然成立。

## 读 GBK 老文件：`-Encoding oem`

```powershell
Get-Content gbk.txt                  # 4 个汉字 → 8 个 U+FFFD
Get-Content gbk.txt -Encoding oem    # 正确
```

pwsh 7 的 `Get-Content` 默认按 UTF-8 解，`.bat`、旧日志这类 GBK 文件必然乱码。`-Encoding Default` 也不救——Win11 开了「使用 UTF-8 提供全球语言支持」之后，`Default` 就是 UTF-8。必须写 `oem`（即代码页 936）。

## 两条语法差异

- `-Encoding Byte` 在 7 里直接报错：`'Byte' is not a supported encoding name`，要改成 `-AsByteStream`。
- `Get-WmiObject` 在 7.7 里**仍然存在**，但它是 `Microsoft.PowerShell.Management` 里的一个兼容函数，不是原生命令。新代码用 `Get-CimInstance`。

## 判据

遇到乱码先问一句：**这个字符串在哪一步被解码？** 是喂给别的进程的 stdin（`$OutputEncoding`）、写进文件的 stdout（重定向路径）、还是 PowerShell 自己捕获的结果（`[Console]::OutputEncoding`）——三处三个开关，换字体、改 locale、重装系统都没用。

固定写法三条：捕获原生命令输出前先设 `[Console]::OutputEncoding`；读 GBK 老文件写 `-Encoding oem`；在 5.1 里往原生命令喂中文之前，先确认 `$OutputEncoding` 不是 US-ASCII。
