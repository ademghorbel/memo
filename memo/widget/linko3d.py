"""CS Linko 3D skin: the official 3D head render, animated per mood.

Same contract as face.py: `draw(canvas, state, t, k)`, plus SIZE, STATES and INK.
Needs Pillow and a render PNG (path from $MEMO_LINKO_IMAGE). Local skin: the
render is IEEE CS artwork and is not shipped in the repo.
"""

from __future__ import annotations

import math
import os
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps, ImageTk

SIZE = 180
STATES = ("tidy", "worried", "bloated", "working", "done", "error")
INK = "#23264a"
SWEAT = "#7cc4f2"
BLUSH = "#f28bb0"
CUBE = ("#5a6fe0", "#7ee0e8", "#9fc8f5")

IMAGE = Path(os.environ.get("MEMO_LINKO_IMAGE",
                            Path.home() / "Downloads" / "GradientBG" / "Linko" / "Linko.png"))
FILL = 0.86  # head size as a share of the window

_cache: dict = {}


def _prepare(k: float) -> dict:
    if k in _cache:
        return _cache[k]
    im = Image.open(IMAGE).convert("RGBA")
    im = im.crop(im.getchannel("A").getbbox())
    a = im.getchannel("A").point(lambda v: 255 if v >= 128 else 0)  # hard edge: no pink fringe
    im.putalpha(a)
    side = int(SIZE * k * FILL)
    scale = side / max(im.size)

    def fit(img, f=1.0):
        w, h = int(img.width * scale * f), int(img.height * scale * f)
        out = img.resize((w, h), Image.LANCZOS)
        out.putalpha(out.getchannel("A").point(lambda v: 255 if v >= 128 else 0))
        return ImageTk.PhotoImage(out)

    grey = ImageOps.grayscale(im.convert("RGB")).convert("RGBA")
    grey.putalpha(a)
    grey = ImageEnhance.Brightness(grey).enhance(1.1)
    pale = ImageEnhance.Color(im).enhance(0.6)
    _cache[k] = {
        "tidy": fit(im), "big": fit(im, 1.1), "error": fit(grey), "worried": fit(pale),
        "h": im.height * scale,
    }
    return _cache[k]


def draw(c, state: str, t: float, k: float = 1.0) -> None:
    c.delete("all")
    imgs = _prepare(k)
    cx, cy = SIZE * k / 2, SIZE * k / 2
    dx, dy = 0.0, 1.5 * k * math.sin(t * 1.6)
    img = imgs["tidy"]

    if state == "working":
        dy -= 6 * k * abs(math.sin(t * 7))
    elif state == "done":
        dy -= 8 * k * abs(math.sin(t * 4))
    elif state == "worried":
        dx = 1.4 * k * math.sin(t * 19)
        img = imgs["worried"]
    elif state == "bloated":
        img = imgs["big"]
    elif state == "error":
        img = imgs["error"]
        dy = 0

    if state == "working":  # little cubes orbit behind and in front
        _orbit(c, cx, cy, t, k, front=False)
    c.create_image(cx + dx, cy + dy, image=img)
    if state == "working":
        _orbit(c, cx, cy, t, k, front=True)

    if state == "done":
        for i in range(5):
            a = t * 3 + i * 1.26
            r = (70 + 6 * math.sin(t * 5 + i)) * k
            x, y = cx + r * math.cos(a), cy + r * 0.8 * math.sin(a)
            s = (3 + 1.5 * math.sin(t * 8 + i)) * k
            c.create_polygon(x, y - 2 * s, x + s * 0.6, y, x, y + 2 * s, x - s * 0.6, y,
                             fill="#ffe27a", outline="")
            c.create_polygon(x - 2 * s, y, x, y + s * 0.6, x + 2 * s, y, x, y - s * 0.6,
                             fill="#ffe27a", outline="")
    elif state == "worried":
        drop = (t * 14) % 30
        x, y = cx + 62 * k, cy - 30 * k + drop * k
        c.create_polygon(x, y - 9 * k, x + 5.5 * k, y + 2 * k, x, y + 7 * k, x - 5.5 * k, y + 2 * k,
                         smooth=True, fill=SWEAT, outline=INK, width=max(1, 1.5 * k))
    elif state == "bloated":
        for sx in (-1, 1):
            x, y = cx + sx * 34 * k, cy + 22 * k + dy
            c.create_oval(x - 9 * k, y - 3.5 * k, x + 9 * k, y + 3.5 * k, fill=BLUSH, outline="")
    elif state == "error":
        x, y = cx + 58 * k, cy - 62 * k
        c.create_text(x, y, text="?", fill=INK, font=("Segoe UI", int(20 * k), "bold"))


def _orbit(c, cx, cy, t, k, front):
    for i in range(6):
        a = t * 2.2 + i * 1.047
        if (math.sin(a) > 0) != front:
            continue
        r = 74 * k
        x, y = cx + r * math.cos(a), cy + 8 * k + r * 0.35 * math.sin(a)
        s = (5 + 2 * math.sin(a)) * k
        col = CUBE[i % 3]
        c.create_rectangle(x - s, y - s, x + s, y + s, fill=col, outline=INK, width=max(1, k))
