"""The on-screen terminal: scrollback, input line, and a nano-style editor."""
import pygame

from . import ui


class Terminal:
    def __init__(self, fonts):
        self.fonts = fonts
        self.lines = []          # list of (text, color)
        self.max_lines = 2000
        self.input = ""
        self.cursor = 0
        self.scroll = 0          # lines scrolled up from bottom
        self.prompt = "$ "
        self.blink = 0.0
        self.show_cursor = True
        self.enabled = True
        self.on_submit = None
        self.history = []
        self.hist_idx = None
        self.saved_input = ""

    def write(self, text, color=ui.FG):
        if text is None:
            return
        for line in text.split("\n"):
            self.lines.append((line, color))
        del self.lines[:-self.max_lines]
        self.scroll = 0

    def write_lines(self, pairs):
        for text, color in pairs:
            self.write(text, color)

    def clear(self):
        self.lines = []

    def set_prompt(self, p):
        self.prompt = p

    # --------------------------------------------------------------- input
    def handle_key(self, event, audio=None):
        if not self.enabled:
            return None
        key = event.key
        mods = event.mod
        ctrl = mods & pygame.KMOD_CTRL
        if key == pygame.K_RETURN or key == pygame.K_KP_ENTER:
            line = self.input
            self.input = ""
            self.cursor = 0
            self.hist_idx = None
            if line.strip():
                self.history.append(line)
            if self.on_submit:
                return self.on_submit(line)
            return None
        if key == pygame.K_BACKSPACE:
            if self.cursor > 0:
                self.input = self.input[:self.cursor - 1] + self.input[self.cursor:]
                self.cursor -= 1
            return None
        if key == pygame.K_DELETE:
            if self.cursor < len(self.input):
                self.input = self.input[:self.cursor] + self.input[self.cursor + 1:]
            return None
        if key == pygame.K_LEFT:
            self.cursor = max(0, self.cursor - 1)
            return None
        if key == pygame.K_RIGHT:
            self.cursor = min(len(self.input), self.cursor + 1)
            return None
        if key == pygame.K_HOME or (ctrl and key == pygame.K_a):
            self.cursor = 0
            return None
        if key == pygame.K_END or (ctrl and key == pygame.K_e):
            self.cursor = len(self.input)
            return None
        if ctrl and key == pygame.K_u:
            self.input = self.input[self.cursor:]
            self.cursor = 0
            return None
        if ctrl and key == pygame.K_k:
            self.input = self.input[:self.cursor]
            return None
        if ctrl and key == pygame.K_c:
            self.write(self.prompt + self.input + "^C", ui.DIM)
            self.input = ""
            self.cursor = 0
            return None
        if ctrl and key == pygame.K_l:
            self.clear()
            return None
        if key == pygame.K_UP:
            self._history_prev()
            return None
        if key == pygame.K_DOWN:
            self._history_next()
            return None
        if key == pygame.K_PAGEUP:
            self.scroll = min(len(self.lines), self.scroll + 10)
            return None
        if key == pygame.K_PAGEDOWN:
            self.scroll = max(0, self.scroll - 10)
            return None
        if key == pygame.K_TAB:
            return ("__TAB__", self.input, self.cursor)
        return None

    def handle_text(self, text):
        if not self.enabled:
            return
        self.input = self.input[:self.cursor] + text + self.input[self.cursor:]
        self.cursor += len(text)

    def set_input(self, text):
        self.input = text
        self.cursor = len(text)

    def _history_prev(self):
        if not self.history:
            return
        if self.hist_idx is None:
            self.saved_input = self.input
            self.hist_idx = len(self.history) - 1
        elif self.hist_idx > 0:
            self.hist_idx -= 1
        self.set_input(self.history[self.hist_idx])

    def _history_next(self):
        if self.hist_idx is None:
            return
        if self.hist_idx < len(self.history) - 1:
            self.hist_idx += 1
            self.set_input(self.history[self.hist_idx])
        else:
            self.hist_idx = None
            self.set_input(self.saved_input)

    # --------------------------------------------------------------- update/draw
    def update(self, dt):
        self.blink += dt
        if self.blink >= 0.53:
            self.blink = 0.0
            self.show_cursor = not self.show_cursor

    def draw(self, surface, rect, show_input=True):
        fonts = self.fonts
        pygame.draw.rect(surface, ui.BG, rect)
        pad = 10
        lh = fonts.line_h
        inner = rect.inflate(-pad * 2, -pad * 2)
        input_h = (lh + 6) if show_input else 0
        view_h = inner.height - input_h
        visible = max(1, view_h // lh)

        total = len(self.lines)
        end = total - self.scroll
        start = max(0, end - visible)
        y = inner.y + (view_h - (end - start) * lh) if (end - start) < visible else inner.y
        y = inner.y
        for i in range(start, end):
            text, color = self.lines[i]
            font = fonts.term_font(text)
            if text:
                surf = font.render(text, True, color)
                surface.blit(surf, (inner.x, y))
            y += lh

        if show_input and self.enabled:
            iy = rect.bottom - pad - lh
            pygame.draw.line(surface, ui.BORDER, (rect.x + pad, iy - 4), (rect.right - pad, iy - 4), 1)
            pfont = fonts.term_font(self.prompt)
            psurf = pfont.render(self.prompt, True, ui.GREEN)
            surface.blit(psurf, (inner.x, iy))
            ix = inner.x + psurf.get_width()
            ifont = fonts.term_font(self.input) if self.input else fonts.mono
            isurf = ifont.render(self.input, True, ui.FG)
            surface.blit(isurf, (ix, iy))
            if self.show_cursor:
                cx = ix + ifont.size(self.input[:self.cursor])[0]
                cw = ifont.size("M")[0]
                cur = pygame.Surface((cw, lh), pygame.SRCALPHA)
                cur.fill((*ui.GREEN, 150))
                surface.blit(cur, (cx, iy))
                if self.cursor < len(self.input):
                    ch = self.input[self.cursor]
                    surface.blit(ifont.render(ch, True, ui.BG), (cx, iy))

        # scroll indicator
        if self.scroll > 0:
            tag = f" [scrolled {self.scroll} lines - PgDn to return] "
            s = fonts.mono_small.render(tag, True, ui.AMBER)
            surface.blit(s, (rect.right - s.get_width() - pad, rect.y + 2))


class NanoEditor:
    """A minimal full-screen text editor (save Ctrl-O, exit Ctrl-X)."""

    def __init__(self, fonts, path, content):
        self.fonts = fonts
        self.path = path
        self.lines = content.split("\n")
        if self.lines and self.lines[-1] == "" and content.endswith("\n"):
            self.lines.pop()
        if not self.lines:
            self.lines = [""]
        self.row = 0
        self.col = 0
        self.top = 0
        self.dirty = False
        self.message = ""
        self.result = None       # ("save", text) / ("exit", None)
        self.confirm_exit = False

    def text(self):
        return "\n".join(self.lines) + "\n"

    def handle_key(self, event):
        mods = event.mod
        ctrl = mods & pygame.KMOD_CTRL
        key = event.key
        if ctrl and key == pygame.K_o:
            self.result = ("save", self.text())
            self.dirty = False
            self.message = f"[ Wrote {len(self.lines)} lines ]"
            return
        if ctrl and key == pygame.K_x:
            if self.dirty and not self.confirm_exit:
                self.confirm_exit = True
                self.message = "Save modified buffer? Press Ctrl-O to save, or Ctrl-X again to discard."
                return
            self.result = ("exit", None)
            return
        self.confirm_exit = False
        self.message = ""
        if key == pygame.K_RETURN:
            cur = self.lines[self.row]
            self.lines[self.row] = cur[:self.col]
            self.lines.insert(self.row + 1, cur[self.col:])
            self.row += 1
            self.col = 0
            self.dirty = True
        elif key == pygame.K_BACKSPACE:
            if self.col > 0:
                cur = self.lines[self.row]
                self.lines[self.row] = cur[:self.col - 1] + cur[self.col:]
                self.col -= 1
                self.dirty = True
            elif self.row > 0:
                prev = self.lines[self.row - 1]
                self.col = len(prev)
                self.lines[self.row - 1] = prev + self.lines[self.row]
                del self.lines[self.row]
                self.row -= 1
                self.dirty = True
        elif key == pygame.K_DELETE:
            cur = self.lines[self.row]
            if self.col < len(cur):
                self.lines[self.row] = cur[:self.col] + cur[self.col + 1:]
                self.dirty = True
            elif self.row < len(self.lines) - 1:
                self.lines[self.row] += self.lines[self.row + 1]
                del self.lines[self.row + 1]
                self.dirty = True
        elif key == pygame.K_LEFT:
            if self.col > 0:
                self.col -= 1
            elif self.row > 0:
                self.row -= 1
                self.col = len(self.lines[self.row])
        elif key == pygame.K_RIGHT:
            if self.col < len(self.lines[self.row]):
                self.col += 1
            elif self.row < len(self.lines) - 1:
                self.row += 1
                self.col = 0
        elif key == pygame.K_UP:
            if self.row > 0:
                self.row -= 1
                self.col = min(self.col, len(self.lines[self.row]))
        elif key == pygame.K_DOWN:
            if self.row < len(self.lines) - 1:
                self.row += 1
                self.col = min(self.col, len(self.lines[self.row]))
        elif key == pygame.K_HOME:
            self.col = 0
        elif key == pygame.K_END:
            self.col = len(self.lines[self.row])

    def handle_text(self, text):
        cur = self.lines[self.row]
        self.lines[self.row] = cur[:self.col] + text + cur[self.col:]
        self.col += len(text)
        self.dirty = True

    def draw(self, surface, rect):
        fonts = self.fonts
        surface.fill(ui.BG, rect)
        lh = fonts.line_h
        # header
        hdr = pygame.Rect(rect.x, rect.y, rect.width, lh + 8)
        pygame.draw.rect(surface, ui.SELECT_BG, hdr)
        title = f"  GNU nano    File: {self.path}" + ("   Modified" if self.dirty else "")
        surface.blit(fonts.term_font(title).render(title, True, ui.BRIGHT), (rect.x + 4, rect.y + 4))
        # body
        pad = 8
        body_top = rect.y + lh + 12
        footer_h = lh * 2 + 10
        rows = max(1, (rect.bottom - footer_h - body_top) // lh)
        if self.row < self.top:
            self.top = self.row
        elif self.row >= self.top + rows:
            self.top = self.row - rows + 1
        y = body_top
        for i in range(self.top, min(len(self.lines), self.top + rows)):
            text = self.lines[i]
            font = fonts.term_font(text)
            if text:
                surface.blit(font.render(text, True, ui.FG), (rect.x + pad, y))
            if i == self.row:
                cx = rect.x + pad + font.size(text[:self.col])[0]
                cur = pygame.Surface((font.size("M")[0], lh), pygame.SRCALPHA)
                cur.fill((*ui.GREEN, 140))
                surface.blit(cur, (cx, y))
                if self.col < len(text):
                    surface.blit(font.render(text[self.col], True, ui.BG), (cx, y))
            y += lh
        # footer
        fy = rect.bottom - footer_h
        if self.message:
            msurf = fonts.ui_small.render(self.message, True, ui.AMBER)
            surface.blit(msurf, (rect.centerx - msurf.get_width() // 2, fy - 2))
        keys = [("^O", "Write Out"), ("^X", "Exit"), ("^K", ""), ("Arrows", "Move")]
        kx = rect.x + pad
        ky = rect.bottom - lh - 2
        for combo, label in keys:
            c = fonts.mono_small.render(combo, True, ui.BG)
            box = pygame.Surface((c.get_width() + 6, fonts.small_line_h), pygame.SRCALPHA)
            box.fill(ui.BRIGHT)
            box.blit(c, (3, 0))
            surface.blit(box, (kx, ky))
            kx += box.get_width() + 4
            l = fonts.mono_small.render(label, True, ui.FG)
            surface.blit(l, (kx, ky))
            kx += l.get_width() + 18
