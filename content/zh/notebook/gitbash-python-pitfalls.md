---
title: Git Bash 里跑 Python 的三个坑
slug: gitbash-python-pitfalls
date: 2026-10-30
tags: ["Windows", "Python"]
---

在 Windows 上用 Git Bash 写 Python，有三个坑反复踩。

## 一、输出中文报 UnicodeEncodeError

Git Bash 下 Python 的 stdout 默认是 GBK，打印 `│` `█` 这类字符直接抛异常。

```python
import sys, io
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
```

放在脚本最开头，一行解决。

## 二、heredoc 里的反斜杠会被吃掉

下面这种写法，正则里的 `\\` 会在传递过程中少一层：

```bash
python3 -c "import re; re.findall('\\\\d+', s)"
```

看起来没问题，实际上静默返回 0 个结果，看起来像"数据里没有"。

**对策**：只要 Python 代码里有反斜杠、中文引号，或者超过 50 行，就不要经 Bash 传递——写到 `.py` 文件里再执行。

## 三、中文路径下的 `cv2.imread` 返回 None

OpenCV 遇到中文路径不会报错，只会返回 `None`，然后你在下游拿到一个 `NoneType` 异常，查半天找不到原因。

```python
import numpy as np, cv2
img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
```

---

这三个坑的共同点是：**都不报明显的错**。第一个报的是编码异常但位置迷惑，后两个干脆静默。所以排查这类问题时，先怀疑路径和编码，别先怀疑算法。
