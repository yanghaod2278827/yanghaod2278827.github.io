---
title: The black background was filled in during conversion, not by the transparency
slug: alpha-png-black-background
date: 2026-11-25
tags: ["Pillow", "Image Processing", "Typesetting"]
summary: Converting an RGBA image with convert('RGB') drops alpha and leaves the zeros underneath — which lands in Word as a solid black block. Composite onto white first.
---

## Symptom

A diagram looks fine in an image viewer or browser with a transparent background. Drop it into Word, or export it as JPEG, and the transparent area becomes solid black. The usual first guess is "Word is rendering it wrong", but the same block appears in other software for the same file.

## Cause

`Image.convert('RGB')` keeps only the colour channels — alpha is discarded. The colour values of transparent pixels are usually `(0, 0, 0)`. Transparent is not white; once alpha is gone, the zeros become visible.

## Proof

A 10×10 RGBA image with the left half fully transparent:

```python
im.convert('RGB').getpixel((0, 0))          # (0, 0, 0)       ← the black block
bg = Image.new('RGB', im.size, 'white')
bg.paste(im, mask=im.split()[-1])
bg.getpixel((0, 0))                          # (255, 255, 255) ← the white ground
```

The same cause has two more entrances: indexed (P-mode) images store transparency in `info['transparency']`, which `convert('RGB')` also drops; and JPEG has no alpha channel at all, so transparent areas have to become some colour, usually black. "Export as JPEG" and `convert('RGB')` are two spellings of the same mistake.

## Fix

```python
from PIL import Image

im = Image.open(src).convert('RGBA')
bg = Image.new('RGB', im.size, 'white')
bg.paste(im, mask=im.split()[-1])
bg.save(dst, 'PNG')
```

The `mask` must be the alpha channel itself. Drop it and `paste` becomes "overwrite": the transparent pixels' colour is written through, and the whole exercise is wasted. Three habits to go with it: keep delivered images as PNG; never hand Word an alpha-bearing TIFF; never let a batch script contain a bare `convert('RGB')`.

## Why viewers look fine and Word does not

Viewers **lay down a backing colour** (white or a chequerboard) before drawing an alpha image, so transparency shows as white. Word receives opaque RGB and paints the zeros. Same data, two rendering conventions — the difference you see is not in the image, it is in the program looking at it.

## Batch check

Visual inspection misses one eventually, and this error tends not to come alone. Before delivery, extract every image from the docx/pptx and measure the share of near-black pixels; anything above a threshold is a candidate, and the number of candidates must be zero. SEM images are legitimately black and logos are legitimately transparent — those go on an allowlist with a stated reason. Otherwise the check goes from "0" to "many" and within a few runs nobody reads the alerts.

The point of the check is not to find this one image but to find **which generation path skipped the white composite**. You fix that exit, not the picture. Both of my recurrences came from a newly added script that converted images its own way — nobody was wrong, the conversion was just implemented twice.

## Rule

Seeing a black block, first ask **what colour the transparent area was filled with**, and only then suspect Word, the printer or the display. Transparency is information; dropping it requires deliberately choosing a colour to put underneath.
