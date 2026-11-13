---
title: Three ways Python on Git Bash bites you
slug: gitbash-python-pitfalls
date: 2026-10-30
tags: ["Windows", "Python"]
---

Writing Python on Git Bash in Windows, three traps keep coming back.

## One: printing Unicode raises UnicodeEncodeError

Under Git Bash, Python's stdout defaults to GBK. Printing characters like `│` or `█` raises immediately.

```python
import sys, io
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
```

Put it at the top of the script and you're done.

## Two: backslashes get eaten in heredocs

With a construction like this, the `\\` in the regex loses a level on the way through:

```bash
python3 -c "import re; re.findall('\\\\d+', s)"
```

Looks fine. In practice it silently returns zero matches, which reads as "the data isn't there".

**The fix**: if the Python has backslashes, Chinese quotes, or more than about 50 lines, don't pass it through Bash at all — write a `.py` file and run that.

## Three: `cv2.imread` returns None on Chinese paths

OpenCV doesn't complain about a path containing non-ASCII characters; it just returns `None`, and you get a `NoneType` error further downstream with no clue why.

```python
import numpy as np, cv2
img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
```

---

What these three have in common: **none of them fail loudly**. The first raises, but at a confusing place; the other two are silent. When debugging this class of problem, suspect paths and encodings before you suspect the algorithm.
