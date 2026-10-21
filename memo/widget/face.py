"""Draws Memo's face on a tkinter canvas.

Pure drawing, no window logic: `draw(canvas, state, t, k)` redraws the whole
face for animation time `t` (seconds) at scale `k`. A different skin is just a
different module with the same `draw` function.
"""

from __future__ import annotations

import math

SIZE = 180  # design units; the window multiplies everything by k

STATES = ("tidy", "worried", "bloated", "working", "done", "error")

INK = "#2b2b3a"
STREAK = "#ff5fa2"  # the emo hair streak
WHITE = "#ffffff"
BLUSH = "#f28b82"
SWEAT = "#7cc4f2"
SKIN = {
    "tidy": "#a8e6cf",
    "worried": "#f6e3a1",
    "bloated": "#f7b2a8",
    "working": "#c9b8f0",
    "done": "#a8e6cf",
    "error": "#c9c9d1",
}


def draw(c, state: str, t: float, k: float = 1.0) -> None:
    c.delete("all")
    s = lambda *xy: [v * k for v in xy]  # noqa: E731  design units -> pixels
    w = lambda v: max(1.0, v * k)  # noqa: E731  line width

    breathe = math.sin(t * 1.6)
    cx, cy = 90.0, 104.0
    if state == "working":
        cy -= 3 * abs(math.sin(t * 7))  # little hops while busy
    rx = 60 + (8 if state == "bloated" else 0) + 1.2 * breathe
    ry = 56 - 1.2 * breathe
    skin = SKIN.get(state, SKIN["tidy"])

    # Body
    c.create_oval(*s(cx - rx, cy - ry, cx + rx, cy + ry), fill=skin, outline=INK, width=w(3))

    # Cheeks
    if state == "bloated":
        puff = 11 + 1.5 * math.sin(t * 3)
        for side in (-1, 1):
            x = cx + side * (rx - 18)
            c.create_oval(*s(x - puff, cy + 4, x + puff, cy + 4 + 2 * puff * 0.8), fill=BLUSH, outline="")
    elif state == "done":
        for side in (-1, 1):
            x = cx + side * 38
            c.create_oval(*s(x - 8, cy + 12, x + 8, cy + 20), fill=BLUSH, outline="")

    _eyes(c, state, t, cx, cy, skin, s, w)
    _mouth(c, state, t, cx, cy, s, w)
    _hair(c, cx, cy, rx, ry, s, w)

    if state == "worried":
        drop = (t * 14) % 34
        x, y = cx + rx * 0.78, cy - ry * 0.45 + drop
        c.create_polygon(*s(x, y - 9, x + 5.5, y + 2, x, y + 7, x - 5.5, y + 2),
                         smooth=True, fill=SWEAT, outline=INK, width=w(1.5))
    if state == "working":
        for i in range(3):  # thinking dots
            on = int(t * 3) % 4 > i
            x = cx + 40 + i * 12
            c.create_oval(*s(x - 3, 30 - 3, x + 3, 30 + 3), fill=INK if on else WHITE, outline=INK, width=w(1.5))


def _hair(c, cx, cy, rx, ry, s, w):
    # A cap on top with a long side bang sweeping down toward the left eye.
    pts = [
        (cx - rx * 0.97, cy - ry * 0.30),
        (cx - rx * 0.80, cy - ry * 0.85),
        (cx - rx * 0.10, cy - ry * 1.10),
        (cx + rx * 0.70, cy - ry * 0.92),
        (cx + rx * 0.99, cy - ry * 0.25),
        (cx + rx * 0.62, cy - ry * 0.55),
        (cx + rx * 0.15, cy - ry * 0.55),
        (cx - rx * 0.40, cy - ry * 0.38),
        (cx - rx * 0.62, cy - ry * 0.18),
        (cx - rx * 0.82, cy - ry * 0.05),
    ]
    flat = [v for p in pts for v in p]
    c.create_polygon(*s(*flat), smooth=True, fill=INK, outline=INK, width=w(2))
    c.create_line(*s(cx + rx * 0.55, cy - ry * 0.80, cx + rx * 0.05, cy - ry * 0.72,
                     cx - rx * 0.45, cy - ry * 0.50),
                  smooth=True, fill=STREAK, width=w(4), capstyle="round")


def _eyes(c, state, t, cx, cy, skin, s, w):
    ey = cy - 2
    blink = (t % 4.3) < 0.14 and state in ("tidy", "worried", "bloated")
    dx = 0.0
    if state == "worried":
        g = math.sin(t * 0.9)
        dx = 5 if g > 0.35 else -5 if g < -0.35 else 0
    elif state == "working":
        dx = 7 * math.sin(t * 5)

    for side in (-1, 1):
        ex = cx + side * 23 + dx
        if state == "error":
            for a, b in ((-7, 7), (7, -7)):
                c.create_line(*s(ex - 7, ey + a, ex + 7, ey + b), fill=INK, width=w(3.5), capstyle="round")
        elif state == "done":
            c.create_arc(*s(ex - 9, ey - 5, ex + 9, ey + 11), start=20, extent=140,
                         style="arc", outline=INK, width=w(3.5))
        elif blink:
            c.create_line(*s(ex - 8, ey + 1, ex + 8, ey + 1), fill=INK, width=w(3), capstyle="round")
        else:
            c.create_oval(*s(ex - 8, ey - 11, ex + 8, ey + 11), fill=INK, outline="")
            c.create_oval(*s(ex - 5, ey - 8, ex, ey - 3), fill=WHITE, outline="")
            if state == "bloated":  # heavy eyelids
                c.create_rectangle(*s(ex - 10, ey - 13, ex + 10, ey - 1), fill=skin, outline="")
                c.create_line(*s(ex - 9, ey - 1, ex + 9, ey - 1), fill=INK, width=w(3), capstyle="round")


def _mouth(c, state, t, cx, cy, s, w):
    my = cy + 24
    if state == "tidy":
        c.create_arc(*s(cx - 9, my - 9, cx + 9, my + 5), start=200, extent=140,
                     style="arc", outline=INK, width=w(3))
    elif state == "done":
        c.create_arc(*s(cx - 15, my - 16, cx + 15, my + 8), start=190, extent=160,
                     style="chord", fill=INK, outline=INK, width=w(2))
    elif state == "worried":
        pts = []
        for i in range(7):
            x = cx - 12 + i * 4
            pts += [x, my + (2.5 if i % 2 else -2.5)]
        c.create_line(*s(*pts), smooth=True, fill=INK, width=w(3), capstyle="round")
    elif state == "bloated":
        r = 3 + 0.8 * math.sin(t * 3)
        c.create_oval(*s(cx - r, my - r, cx + r, my + r), fill=INK, outline="")
    elif state == "working":
        h = 1.5 + 6 * abs(math.sin(t * 9))  # munching
        c.create_oval(*s(cx - 8, my - h, cx + 8, my + h), fill=INK, outline="")
    else:  # error
        c.create_line(*s(cx - 12, my, cx - 6, my - 3, cx, my, cx + 6, my - 3, cx + 12, my),
                      fill=INK, width=w(3), capstyle="round")
