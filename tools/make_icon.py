#!/usr/bin/env python3
"""Draw the CyberDefence app icon: a glowing shield over a terminal prompt."""
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")

SIZE = 512
BG0 = (8, 14, 22)
BG1 = (12, 24, 36)
GREEN = (64, 230, 160)
CYAN = (70, 200, 230)
DARK = (6, 10, 16)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw(size=SIZE):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # rounded background
    r = int(size * 0.18)
    for y in range(size):
        col = lerp(BG1, BG0, y / size)
        d.line([(0, y), (size, y)], fill=col + (255,))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=255)
    img.putalpha(mask)
    d = ImageDraw.Draw(img)

    # shield outline
    cx = size / 2
    top = size * 0.16
    w = size * 0.30
    midy = size * 0.46
    bot = size * 0.86
    pts = [(cx, top), (cx + w, top + size * 0.09), (cx + w, midy),
           (cx, bot), (cx - w, midy), (cx - w, top + size * 0.09)]
    # glow
    for i, width in enumerate((18, 12, 6)):
        glow = lerp(DARK, GREEN, 0.4 + i * 0.3)
        d.line(pts + [pts[0]], fill=glow + (120,), width=width, joint="curve")
    d.polygon(pts, fill=(14, 30, 40, 235), outline=GREEN + (255,))
    d.line(pts + [pts[0]], fill=GREEN + (255,), width=max(2, size // 90), joint="curve")

    # terminal prompt inside shield  >_
    fs = size * 0.11
    px = cx - size * 0.15
    py = midy - size * 0.10
    d.line([(px, py), (px + fs * 0.7, py + fs * 0.55), (px, py + fs * 1.1)],
           fill=CYAN + (255,), width=max(3, size // 64), joint="curve")
    # cursor underscore
    d.line([(px + fs * 0.9, py + fs * 1.1), (px + fs * 2.0, py + fs * 1.1)],
           fill=GREEN + (255,), width=max(3, size // 64))

    # small check mark at bottom of shield (defended)
    chx = cx - size * 0.09
    chy = bot - size * 0.22
    d.line([(chx, chy), (chx + size * 0.06, chy + size * 0.07),
            (chx + size * 0.18, chy - size * 0.10)],
           fill=GREEN + (255,), width=max(4, size // 48), joint="curve")
    return img


def main():
    os.makedirs(ASSETS, exist_ok=True)
    master = draw(SIZE)
    png = os.path.join(ASSETS, "icon.png")
    master.save(png)
    print("->", png)
    ico = os.path.join(ASSETS, "icon.ico")
    master.save(ico, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("->", ico)


if __name__ == "__main__":
    main()
