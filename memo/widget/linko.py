"""CS Linko skin: a cloud of light-blue cubes wearing round glasses.

Same contract as face.py: `draw(canvas, state, t, k)`, plus SIZE, STATES and INK.
Cubes are drawn as simple 3D boxes (front, top and right faces) back to front.
"""

from __future__ import annotations

import math

SIZE = 180
STATES = ("tidy", "worried", "bloated", "working", "done", "error")

INK = "#23264a"     # glasses, eyes and smile
SHINE = "#4a4f86"   # glossy rim on the eyes
WHITE = "#ffffff"
SWEAT = "#7cc4f2"
BLUSH = "#f28bb0"

# (front, top, right side, edge) per mood
BLUE = ("#93d4f2", "#c2eafb", "#64b2dc", "#78c0e4")
PALETTE = {
    "tidy": BLUE,
    "working": BLUE,
    "done": BLUE,
    "worried": ("#a9d6ee", "#d3ecf8", "#7fb4d2", "#90c3df"),
    "bloated": ("#9cc8f0", "#c9e2fb", "#6c9fd6", "#82b3e2"),
    "error": ("#c4c9d4", "#e0e3ea", "#9aa1b0", "#aeb4c1"),
}

# Cluster cubes (x, y, size) in design units, roughly back to front.
CLUSTER = [
    (96, 34, 40), (60, 66, 38), (104, 56, 46), (126, 76, 30),
    (44, 92, 34), (76, 82, 42), (114, 96, 38),
    (48, 114, 38), (84, 112, 38), (118, 120, 30), (68, 130, 32),
]
# Small floating cubes (x, y, size, phase)
FLOATERS = [
    (34, 26, 9, 0.0), (58, 16, 11, 1.3), (40, 48, 12, 2.1), (68, 42, 10, 0.7),
    (60, 162, 7, 1.8), (100, 158, 6, 2.7), (128, 154, 10, 0.4), (152, 44, 8, 3.1),
]

CX, CY = 90.0, 96.0  # cluster center, used for spreading and orbiting


def _cube(c, x, y, size, pal, s, w):
    front, top, side, edge = pal
    d = size * 0.26
    c.create_polygon(*s(x, y, x + d, y - d, x + size + d, y - d, x + size, y),
                     fill=top, outline=edge, width=w(1))
    c.create_polygon(*s(x + size, y, x + size + d, y - d, x + size + d, y + size - d, x + size, y + size),
                     fill=side, outline=edge, width=w(1))
    c.create_rectangle(*s(x, y, x + size, y + size), fill=front, outline=edge, width=w(1))


def draw(c, state: str, t: float, k: float = 1.0) -> None:
    c.delete("all")
    s = lambda *xy: [v * k for v in xy]  # noqa: E731  design units -> pixels
    w = lambda v: max(1.0, v * k)  # noqa: E731  line width
    pal = PALETTE.get(state, BLUE)

    bob = 1.5 * math.sin(t * 1.6)
    if state == "working":
        bob -= 3 * abs(math.sin(t * 7))
    spread = 1.13 if state == "bloated" else 1.0
    if state == "bloated":
        spread += 0.02 * math.sin(t * 3)

    # Floating cubes: drift gently, orbit while working, fly out when done.
    for i, (x, y, size, ph) in enumerate(FLOATERS):
        fx, fy = x, y + 3 * math.sin(t * 1.4 + ph)
        if state == "working":
            a = t * 2.2 + ph * 2
            r = 70 + 6 * math.sin(ph)
            fx, fy = CX + r * math.cos(a) - size / 2, CY + 6 + r * 0.85 * math.sin(a) - size / 2
        elif state == "done":
            fx, fy = CX + (fx - CX) * 1.08, CY + (fy - CY) * 1.08 - 2 * abs(math.sin(t * 4 + ph))
        elif state == "worried":
            fx += 1.2 * math.sin(t * 17 + i)
        _cube(c, fx, fy + bob * 0.5, size, pal, s, w)

    # The cube cloud (the head).
    for i, (x, y, size) in enumerate(CLUSTER):
        mx, my = x + size / 2, y + size / 2
        mx, my = CX + (mx - CX) * spread, CY + (my - CY) * spread
        if state == "worried":
            mx += 0.8 * math.sin(t * 19 + i * 1.7)
        _cube(c, mx - size / 2, my - size / 2 + bob, size, pal, s, w)

    _face(c, state, t, bob, pal, s, w)


def _face(c, state, t, bob, pal, s, w):
    ly = 122 + bob
    tilt = 4 if state == "error" else 0
    lenses = ((62, ly + tilt), (118, ly - tilt))
    r = 24

    # Cheeks under the glasses when happy or puffed up.
    if state in ("done", "bloated"):
        for (lx, y) in lenses:
            c.create_oval(*s(lx - 10, y + 13, lx + 10, y + 20), fill=BLUSH, outline="")

    _eyes(c, state, t, lenses, pal, s, w)

    # Glasses: two round frames and a little bridge loop.
    for (lx, y) in lenses:
        c.create_oval(*s(lx - r, y - r, lx + r, y + r), outline=INK, width=w(3))
    bx, by = 90, (lenses[0][1] + lenses[1][1]) / 2 - 5
    c.create_arc(*s(bx - 6, by - 6, bx + 6, by + 6), start=0, extent=180, style="arc", outline=INK, width=w(3))

    _smile(c, state, t, bx, by + 10, s, w)

    if state == "worried":
        drop = (t * 14) % 30
        x, y = 150, 70 + drop
        c.create_polygon(*s(x, y - 9, x + 5.5, y + 2, x, y + 7, x - 5.5, y + 2),
                         smooth=True, fill=SWEAT, outline=INK, width=w(1.5))


def _eyes(c, state, t, lenses, pal, s, w):
    blink = (t % 4.3) < 0.14 and state in ("tidy", "worried", "bloated")
    dx = 0.0
    if state == "worried":
        g = math.sin(t * 0.9)
        dx = 6 if g > 0.35 else -6 if g < -0.35 else 0
    elif state == "working":
        dx = 7 * math.sin(t * 5)

    for (lx, y) in lenses:
        ex, ey = lx + dx, y - 1
        if state == "error":
            for a, b in ((-7, 7), (7, -7)):
                c.create_line(*s(ex - 7, ey + a, ex + 7, ey + b), fill=INK, width=w(4), capstyle="round")
        elif state == "done":
            c.create_arc(*s(ex - 10, ey - 6, ex + 10, ey + 12), start=20, extent=140,
                         style="arc", outline=INK, width=w(4.5))
        elif blink:
            c.create_line(*s(ex - 10, ey + 1, ex + 10, ey + 1), fill=INK, width=w(4), capstyle="round")
        else:
            c.create_oval(*s(ex - 12, ey - 12, ex + 12, ey + 12), fill=INK, outline=SHINE, width=w(1.5))
            c.create_oval(*s(ex - 7, ey - 8, ex - 1, ey - 3), fill=WHITE, outline="")
            c.create_oval(*s(ex + 4, ey + 4, ex + 7, ey + 7), fill=SHINE, outline="")
            if state == "bloated":  # heavy lids
                c.create_rectangle(*s(ex - 13, ey - 13, ex + 13, ey - 2), fill=pal[0], outline="")
                c.create_line(*s(ex - 12, ey - 2, ex + 12, ey - 2), fill=INK, width=w(3), capstyle="round")


def _smile(c, state, t, x, y, s, w):
    if state == "done":  # big open smile
        c.create_arc(*s(x - 13, y - 12, x + 13, y + 12), start=190, extent=160,
                     style="chord", fill=INK, outline=INK, width=w(2))
    elif state == "worried":
        pts = []
        for i in range(6):
            pts += [x - 10 + i * 4, y + 3 + (2.5 if i % 2 else -2.5)]
        c.create_line(*s(*pts), smooth=True, fill=INK, width=w(4), capstyle="round")
    elif state == "working":
        h = 2 + 5 * abs(math.sin(t * 9))  # munching
        c.create_oval(*s(x - 7, y + 2 - h, x + 7, y + 2 + h), fill=INK, outline="")
    elif state == "error":
        c.create_line(*s(x - 10, y + 4, x + 10, y + 4), fill=INK, width=w(4), capstyle="round")
    else:  # the curly "u" smile under the bridge
        c.create_line(*s(x - 11, y - 2, x - 6, y + 6, x, y + 8, x + 6, y + 6, x + 11, y - 2),
                      smooth=True, fill=INK, width=w(7), capstyle="round")
