"""Shared UI helpers: colour theme and a font set with CJK fallback."""
import pygame

from .paths import asset

# ------------------------------------------------------------------ theme
BG = (10, 16, 22)
BG_PANEL = (16, 24, 32)
BG_INPUT = (14, 22, 30)
FG = (210, 225, 220)
DIM = (120, 140, 140)
GREEN = (80, 230, 150)
BRIGHT = (150, 255, 200)
CYAN = (90, 205, 230)
AMBER = (240, 190, 90)
RED = (240, 110, 110)
BLUE = (120, 170, 240)
MAGENTA = (210, 140, 230)
SELECT_BG = (28, 46, 56)
BORDER = (40, 60, 70)
SCAN = (0, 0, 0)

SEVERITY = {"crit": RED, "warn": AMBER, "info": CYAN, "ok": GREEN}


class Fonts:
    """Holds the fonts and picks a CJK-capable one for non-latin text."""

    def __init__(self, scale=1.0):
        self.scale = scale
        s = lambda px: max(10, int(px * scale))
        self.mono = pygame.font.Font(asset("fonts", "DejaVuSansMono.ttf"), s(18))
        self.mono_small = pygame.font.Font(asset("fonts", "DejaVuSansMono.ttf"), s(15))
        self.cjk = pygame.font.Font(asset("fonts", "MPLUS1p-Regular.ttf"), s(18))
        self.cjk_small = pygame.font.Font(asset("fonts", "MPLUS1p-Regular.ttf"), s(15))
        self.ui = pygame.font.Font(asset("fonts", "MPLUS1p-Regular.ttf"), s(20))
        self.ui_bold = pygame.font.Font(asset("fonts", "MPLUS1p-Bold.ttf"), s(22))
        self.ui_small = pygame.font.Font(asset("fonts", "MPLUS1p-Regular.ttf"), s(16))
        self.h1 = pygame.font.Font(asset("fonts", "MPLUS1p-Bold.ttf"), s(44))
        self.h2 = pygame.font.Font(asset("fonts", "MPLUS1p-Bold.ttf"), s(28))
        self.cell_w = self.mono.size("M")[0]
        self.line_h = self.mono.get_linesize()
        self.small_line_h = self.mono_small.get_linesize()

    def term_font(self, text, small=False):
        """Monospace for latin, CJK font for lines containing wide chars."""
        if any(ord(c) > 0x2500 for c in text):
            return self.cjk_small if small else self.cjk
        return self.mono_small if small else self.mono


def has_cjk(text):
    return any(ord(c) > 0x2E00 for c in text)


def draw_scanlines(surface, alpha=18):
    w, h = surface.get_size()
    line = pygame.Surface((w, 1), pygame.SRCALPHA)
    line.fill((0, 0, 0, alpha))
    for y in range(0, h, 3):
        surface.blit(line, (0, y))


def wrap_text(text, font, max_w):
    """Word-wrap, preserving explicit newlines and leading spaces."""
    out = []
    for raw in text.split("\n"):
        if not raw:
            out.append("")
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        prefix = " " * indent
        words = raw.split(" ")
        line = ""
        for word in words:
            trial = word if not line else line + " " + word
            if font.size(trial)[0] <= max_w:
                line = trial
            else:
                if line:
                    out.append(line)
                # hard-break very long words
                if font.size(word)[0] > max_w:
                    chunk = prefix
                    for ch in word:
                        if font.size(chunk + ch)[0] > max_w and chunk.strip():
                            out.append(chunk)
                            chunk = prefix + ch
                        else:
                            chunk += ch
                    line = chunk
                else:
                    line = prefix + word if not line else word
        out.append(line)
    return out
