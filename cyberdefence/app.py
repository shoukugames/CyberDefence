"""CyberDefence - entry point and scene manager (all terminal, pygame-rendered)."""
import os
import sys
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

from . import __version__, ui  # noqa: E402
from .audio import Audio  # noqa: E402
from .credits import CREDITS  # noqa: E402
from .i18n import I18n  # noqa: E402
from .levels import ALL_LEVELS, make_level  # noqa: E402
from .save import LEVEL_COUNT, Save, fmt_time  # noqa: E402
from .shell import Shell  # noqa: E402
from .system import build  # noqa: E402
from .terminal import NanoEditor, Terminal  # noqa: E402
from .training import LESSONS  # noqa: E402
from .world import World  # noqa: E402

BASE_W, BASE_H = 1120, 720
LEVEL_TIME = 3600   # one hour countdown


class Scene:
    MENU = "menu"
    SELECT = "select"
    GAME = "game"
    TRAINING = "training"
    LESSON = "lesson"
    PROGRESS = "progress"
    RECORDS = "records"
    CREDITS = "credits"
    SETTINGS = "settings"


class App:
    def __init__(self, smoke=None):
        pygame.init()
        try:
            pygame.key.set_repeat(300, 30)
        except pygame.error:
            pass
        self.save = Save()
        self.tr = I18n(self.save.settings.get("lang", "en"))
        self.smoke = smoke
        flags = pygame.RESIZABLE
        self.fullscreen = self.save.settings.get("fullscreen", False)
        if self.fullscreen:
            flags |= pygame.FULLSCREEN
        self.screen = pygame.display.set_mode((BASE_W, BASE_H), flags)
        pygame.display.set_caption("CyberDefence")
        self._set_icon()
        self.fonts = ui.Fonts(scale=self._scale())
        self.audio = Audio(bgm=self.save.settings.get("bgm", True),
                           sfx=self.save.settings.get("sfx", True),
                           volume=self.save.settings.get("volume", 0.6))
        self.clock = pygame.time.Clock()
        self.running = True
        self.scene = Scene.MENU
        self.sel_menu = 0
        self.sel_level = 0
        self.sel_lesson = 0
        self.sel_setting = 0
        self.rec_level = 1
        self.scrolloff = 0
        self.reset_armed = False
        self.game = None
        self.anim = 0.0

    # ------------------------------------------------------------------ setup
    def _set_icon(self):
        try:
            from .paths import asset
            icon = pygame.image.load(asset("icon.png"))
            pygame.display.set_icon(icon)
        except Exception:
            pass

    def _scale(self):
        w, h = self.screen.get_size()
        return max(0.75, min(1.6, min(w / BASE_W, h / BASE_H)))

    def _(self, key, **kw):
        return self.tr(key, **kw)

    # ------------------------------------------------------------------ main loop
    def run(self):
        if self.smoke is not None:
            return self._run_smoke()
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.anim += dt
            self._handle_events()
            self._update(dt)
            self._draw()
            pygame.display.flip()
        self.save.write()
        pygame.quit()
        return 0

    def _run_smoke(self):
        # Headless self-check used by the build to prove the game boots.
        for _ in range(8):
            self._update(1 / 60)
            self._draw()
        self.start_level(1)
        self.game.terminal.on_submit("mission")
        self.game.terminal.on_submit("sudo ufw enable")
        for _ in range(30):
            self._update(0.2)
        with open(self.smoke, "w", encoding="utf-8") as fh:
            fh.write(f"CyberDefence v{__version__} boots OK; "
                     f"levels={LEVEL_COUNT}; scene={self.scene}; lang={self.tr.lang}\n")
        pygame.quit()
        return 0

    # ------------------------------------------------------------------ events
    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                self.screen = pygame.display.set_mode((max(900, event.w), max(600, event.h)), pygame.RESIZABLE)
                self.fonts = ui.Fonts(scale=self._scale())
                if self.game:
                    self.game.fonts = self.fonts
            elif event.type == pygame.KEYDOWN:
                self._on_key(event)
            elif event.type == pygame.TEXTINPUT:
                self._on_text(event)

    def _global_keys(self, event):
        """Language / music / fullscreen toggles available on menu screens."""
        if event.key == pygame.K_l:
            self.tr.toggle()
            self.save.set("lang", self.tr.lang)
            self.audio.play("select")
            return True
        if event.key == pygame.K_m:
            on = self.audio.toggle_bgm()
            self.save.set("bgm", on)
            self.audio.play("select")
            return True
        if event.key == pygame.K_f:
            self._toggle_fullscreen()
            return True
        return False

    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        flags = pygame.RESIZABLE | (pygame.FULLSCREEN if self.fullscreen else 0)
        size = (0, 0) if self.fullscreen else (BASE_W, BASE_H)
        self.screen = pygame.display.set_mode(size, flags)
        self.fonts = ui.Fonts(scale=self._scale())
        if self.game:
            self.game.fonts = self.fonts
        self.save.set("fullscreen", self.fullscreen)

    def _on_key(self, event):
        s = self.scene
        if s == Scene.GAME:
            self.game.on_key(event)
            if self.game.exit_to_menu:
                self.goto_menu()
            return
        if s == Scene.MENU:
            self._key_menu(event)
        elif s == Scene.SELECT:
            self._key_select(event)
        elif s == Scene.TRAINING:
            self._key_training(event)
        elif s == Scene.LESSON:
            self._key_lesson(event)
        elif s == Scene.PROGRESS:
            self._key_scroll_screen(event)
        elif s == Scene.RECORDS:
            self._key_records(event)
        elif s == Scene.CREDITS:
            self._key_scroll_screen(event)
        elif s == Scene.SETTINGS:
            self._key_settings(event)

    def _on_text(self, event):
        if self.scene == Scene.GAME:
            self.game.on_text(event.text)

    # ------------------------------------------------------------------ menu
    MENU_ITEMS = [Scene.SELECT, Scene.TRAINING, Scene.PROGRESS, Scene.RECORDS,
                  Scene.CREDITS, Scene.SETTINGS, "quit"]
    MENU_KEYS = ["menu.play", "menu.training", "menu.progress", "menu.records",
                 "menu.credits", "menu.settings", "menu.quit"]

    def goto_menu(self):
        self.scene = Scene.MENU
        self.game = None
        if self.audio.bgm_on and not pygame.mixer.music.get_busy() if self.audio.ok else False:
            self.audio.start_music()

    def _key_menu(self, event):
        if self._global_keys(event):
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self.sel_menu = (self.sel_menu - 1) % len(self.MENU_ITEMS)
            self.audio.play("move")
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.sel_menu = (self.sel_menu + 1) % len(self.MENU_ITEMS)
            self.audio.play("move")
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.audio.play("select")
            target = self.MENU_ITEMS[self.sel_menu]
            if target == "quit":
                self.running = False
            elif target == Scene.SELECT:
                self.scene = Scene.SELECT
            else:
                self.scene = target
                self.scrolloff = 0
        elif event.key == pygame.K_ESCAPE:
            self.running = False

    # ------------------------------------------------------------------ level select
    def _key_select(self, event):
        if self._global_keys(event):
            return
        cols = 2
        n = LEVEL_COUNT
        if event.key in (pygame.K_UP, pygame.K_w):
            self.sel_level = (self.sel_level - cols) % n
            self.audio.play("move")
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.sel_level = (self.sel_level + cols) % n
            self.audio.play("move")
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self.sel_level = (self.sel_level - 1) % n
            self.audio.play("move")
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self.sel_level = (self.sel_level + 1) % n
            self.audio.play("move")
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.audio.play("select")
            self.start_level(self.sel_level + 1)
        elif event.key == pygame.K_ESCAPE:
            self.scene = Scene.MENU

    def start_level(self, num):
        self.save.start_attempt(num)
        self.audio.play("alert")
        self.game = GameScene(self, num)
        self.scene = Scene.GAME

    # ------------------------------------------------------------------ training
    def _key_training(self, event):
        if self._global_keys(event):
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self.sel_lesson = (self.sel_lesson - 1) % len(LESSONS)
            self.audio.play("move")
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.sel_lesson = (self.sel_lesson + 1) % len(LESSONS)
            self.audio.play("move")
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.audio.play("select")
            self.scene = Scene.LESSON
            self.scrolloff = 0
            self.save.mark_lesson(LESSONS[self.sel_lesson]["key"])
        elif event.key == pygame.K_ESCAPE:
            self.scene = Scene.MENU

    def _key_lesson(self, event):
        if event.key == pygame.K_ESCAPE:
            self.scene = Scene.TRAINING
        elif event.key in (pygame.K_DOWN, pygame.K_j):
            self.scrolloff += 2
        elif event.key in (pygame.K_UP, pygame.K_k):
            self.scrolloff = max(0, self.scrolloff - 2)
        elif event.key == pygame.K_PAGEDOWN:
            self.scrolloff += 12
        elif event.key == pygame.K_PAGEUP:
            self.scrolloff = max(0, self.scrolloff - 12)
        elif event.key in (pygame.K_LEFT,):
            self.sel_lesson = (self.sel_lesson - 1) % len(LESSONS)
            self.scrolloff = 0
            self.save.mark_lesson(LESSONS[self.sel_lesson]["key"])
        elif event.key in (pygame.K_RIGHT,):
            self.sel_lesson = (self.sel_lesson + 1) % len(LESSONS)
            self.scrolloff = 0
            self.save.mark_lesson(LESSONS[self.sel_lesson]["key"])

    def _key_scroll_screen(self, event):
        if event.key == pygame.K_ESCAPE:
            self.scene = Scene.MENU
        elif event.key in (pygame.K_DOWN, pygame.K_j):
            self.scrolloff += 2
        elif event.key in (pygame.K_UP, pygame.K_k):
            self.scrolloff = max(0, self.scrolloff - 2)
        elif event.key == pygame.K_PAGEDOWN:
            self.scrolloff += 12
        elif event.key == pygame.K_PAGEUP:
            self.scrolloff = max(0, self.scrolloff - 12)

    def _key_records(self, event):
        if self._global_keys(event):
            return
        if event.key == pygame.K_ESCAPE:
            self.scene = Scene.MENU
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self.rec_level = (self.rec_level - 2) % LEVEL_COUNT + 1
            self.audio.play("move")
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self.rec_level = self.rec_level % LEVEL_COUNT + 1
            self.audio.play("move")

    def _key_settings(self, event):
        if event.key == pygame.K_ESCAPE:
            self.scene = Scene.MENU
            self.reset_armed = False
            return
        items = ["lang", "bgm", "sfx", "fullscreen", "volume", "reset"]
        if event.key in (pygame.K_UP, pygame.K_w):
            self.sel_setting = (self.sel_setting - 1) % len(items)
            self.reset_armed = False
            self.audio.play("move")
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.sel_setting = (self.sel_setting + 1) % len(items)
            self.reset_armed = False
            self.audio.play("move")
        else:
            self._settings_change(items[self.sel_setting], event)

    def _settings_change(self, item, event):
        left = event.key in (pygame.K_LEFT, pygame.K_a)
        right = event.key in (pygame.K_RIGHT, pygame.K_d)
        enter = event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
        if item == "lang" and (left or right or enter):
            self.tr.toggle()
            self.save.set("lang", self.tr.lang)
            self.audio.play("select")
        elif item == "bgm" and (left or right or enter):
            self.save.set("bgm", self.audio.toggle_bgm())
            self.audio.play("select")
        elif item == "sfx" and (left or right or enter):
            self.audio.sfx_on = not self.audio.sfx_on
            self.save.set("sfx", self.audio.sfx_on)
            self.audio.play("select")
        elif item == "fullscreen" and (left or right or enter):
            self._toggle_fullscreen()
        elif item == "volume":
            if left:
                self.audio.set_volume(self.audio.volume - 0.1)
                self.save.set("volume", round(self.audio.volume, 2))
            elif right:
                self.audio.set_volume(self.audio.volume + 0.1)
                self.save.set("volume", round(self.audio.volume, 2))
        elif item == "reset" and enter:
            if self.reset_armed:
                from .save import _blank
                self.save.data = _blank()
                self.save.data["settings"]["lang"] = self.tr.lang
                self.save.write()
                self.reset_armed = False
                self.audio.play("win")
            else:
                self.reset_armed = True
                self.audio.play("error")

    # ------------------------------------------------------------------ update/draw
    def _update(self, dt):
        if self.scene == Scene.GAME and self.game:
            self.game.update(dt)

    def _draw(self):
        self.screen.fill(ui.BG)
        s = self.scene
        if s == Scene.MENU:
            self._draw_menu()
        elif s == Scene.SELECT:
            self._draw_select()
        elif s == Scene.GAME:
            self.game.draw(self.screen)
        elif s == Scene.TRAINING:
            self._draw_training()
        elif s == Scene.LESSON:
            self._draw_lesson()
        elif s == Scene.PROGRESS:
            self._draw_progress()
        elif s == Scene.RECORDS:
            self._draw_records()
        elif s == Scene.CREDITS:
            self._draw_credits()
        elif s == Scene.SETTINGS:
            self._draw_settings()
        if s != Scene.GAME:
            ui.draw_scanlines(self.screen, 12)

    # ---- drawing helpers
    def _header(self, title_key, subtitle=None):
        w = self.screen.get_width()
        t = self.fonts.h2.render(self._(title_key), True, ui.BRIGHT)
        self.screen.blit(t, (60, 40))
        if subtitle:
            st = self.fonts.ui_small.render(subtitle, True, ui.DIM)
            self.screen.blit(st, (62, 40 + t.get_height() + 2))
        pygame.draw.line(self.screen, ui.BORDER, (60, 110), (w - 60, 110), 1)

    def _footer(self, text):
        w, h = self.screen.get_size()
        s = self.fonts.ui_small.render(text, True, ui.DIM)
        self.screen.blit(s, (60, h - 36))

    def _toggles_hint(self):
        parts = f"L:{self.tr('lang.name')}   M:{self._('set.bgm')} {'ON' if self.audio.bgm_on else 'OFF'}   F:{self._('set.fullscreen')}"
        w = self.screen.get_width()
        s = self.fonts.ui_small.render(parts, True, ui.DIM)
        self.screen.blit(s, (w - s.get_width() - 60, self.screen.get_height() - 36))

    def _draw_menu(self):
        w, h = self.screen.get_size()
        # Title art
        title = self.fonts.h1.render("CyberDefence", True, ui.GREEN)
        glow = self.fonts.h1.render("CyberDefence", True, (20, 60, 45))
        cx = w // 2
        self.screen.blit(glow, (cx - title.get_width() // 2 + 2, 86))
        self.screen.blit(title, (cx - title.get_width() // 2, 84))
        sub = self.fonts.ui.render(self._("app.tagline"), True, ui.CYAN)
        self.screen.blit(sub, (cx - sub.get_width() // 2, 140))
        jp = self.fonts.ui_small.render(self._("app.title") if self.tr.lang == "en" else "CyberDefence", True, ui.DIM)
        self.screen.blit(jp, (cx - jp.get_width() // 2, 174))

        # blinking prompt accent
        if int(self.anim * 2) % 2 == 0:
            p = self.fonts.h2.render(">_", True, ui.AMBER)
            self.screen.blit(p, (cx - title.get_width() // 2 - 54, 86))

        done = self.save.completed_count()
        prog = self.fonts.ui_small.render(self._("sel.complete_count", done=done, total=LEVEL_COUNT), True, ui.AMBER)
        self.screen.blit(prog, (cx - prog.get_width() // 2, 206))

        y = 250
        for i, key in enumerate(self.MENU_KEYS):
            selected = i == self.sel_menu
            label = self._(key)
            color = ui.BRIGHT if selected else ui.FG
            box = pygame.Rect(cx - 180, y, 360, 46)
            if selected:
                pygame.draw.rect(self.screen, ui.SELECT_BG, box, border_radius=6)
                pygame.draw.rect(self.screen, ui.GREEN, box, 1, border_radius=6)
                arrow = self.fonts.ui_bold.render(">", True, ui.GREEN)
                self.screen.blit(arrow, (box.x + 18, y + 8))
            surf = self.fonts.ui_bold.render(label, True, color)
            self.screen.blit(surf, (cx - surf.get_width() // 2, y + 8))
            y += 54

        self._footer(self._("menu.hint.nav"))
        self._toggles_hint()
        ver = self.fonts.ui_small.render(f"v{__version__}", True, ui.DIM)
        self.screen.blit(ver, (w - ver.get_width() - 20, 20))

    def _draw_select(self):
        self._header("sel.title", self._("sel.complete_count",
                                          done=self.save.completed_count(), total=LEVEL_COUNT))
        w, h = self.screen.get_size()
        cols = 2
        cw = (w - 120 - 30) // cols
        ch = 76
        x0, y0 = 60, 140
        for i in range(LEVEL_COUNT):
            r = i // cols
            c = i % cols
            rect = pygame.Rect(x0 + c * (cw + 30), y0 + r * (ch + 14), cw, ch)
            lv = self.save.level(i + 1)
            selected = i == self.sel_level
            bg = ui.SELECT_BG if selected else ui.BG_PANEL
            pygame.draw.rect(self.screen, bg, rect, border_radius=8)
            edge = ui.GREEN if selected else (ui.BORDER if not lv["completed"] else (40, 90, 70))
            pygame.draw.rect(self.screen, edge, rect, 2 if selected else 1, border_radius=8)
            num = self.fonts.h2.render(f"{i+1:02d}", True, ui.GREEN if lv["completed"] else ui.DIM)
            self.screen.blit(num, (rect.x + 14, rect.y + rect.height // 2 - num.get_height() // 2))
            name = self._(f"lvl.{i+1}.name")
            nsurf = self.fonts.ui.render(name, True, ui.BRIGHT if selected else ui.FG)
            self.screen.blit(nsurf, (rect.x + 74, rect.y + 12))
            lvl_cls = ALL_LEVELS[i]
            threat = " / ".join(lvl_cls.threat_tags)
            tsurf = self.fonts.ui_small.render(threat, True, ui.CYAN)
            self.screen.blit(tsurf, (rect.x + 74, rect.y + 40))
            if lv["completed"]:
                badge = self.fonts.ui_small.render("✓ " + self._("common.completed"), True, ui.GREEN)
                self.screen.blit(badge, (rect.right - badge.get_width() - 12, rect.y + 10))
                bt = self.fonts.ui_small.render(self._("common.best") + ": " + fmt_time(lv["best"]), True, ui.AMBER)
                self.screen.blit(bt, (rect.right - bt.get_width() - 12, rect.y + 40))
        self._footer(self._("menu.hint.nav") + "   •   " + self._("sel.start"))
        self._toggles_hint()

    def _draw_training(self):
        self._header("train.title", self._("train.intro"))
        w, h = self.screen.get_size()
        y = 140
        for i, lesson in enumerate(LESSONS):
            selected = i == self.sel_lesson
            rect = pygame.Rect(60, y, w - 120, 46)
            if selected:
                pygame.draw.rect(self.screen, ui.SELECT_BG, rect, border_radius=6)
                pygame.draw.rect(self.screen, ui.GREEN, rect, 1, border_radius=6)
            title = lesson["title"][1] if self.tr.lang == "ja" else lesson["title"][0]
            color = ui.BRIGHT if selected else ui.FG
            self.screen.blit(self.fonts.ui.render(title, True, color), (rect.x + 20, y + 8))
            if lesson["key"] in self.save.data["lessons_read"]:
                r = self.fonts.ui_small.render(self._("train.read"), True, ui.GREEN)
                self.screen.blit(r, (rect.right - r.get_width() - 16, y + 12))
            y += 52
        self._footer(self._("menu.hint.nav"))
        self._toggles_hint()

    def _draw_lesson(self):
        lesson = LESSONS[self.sel_lesson]
        title = lesson["title"][1] if self.tr.lang == "ja" else lesson["title"][0]
        body = lesson["body"][1] if self.tr.lang == "ja" else lesson["body"][0]
        w, h = self.screen.get_size()
        t = self.fonts.h2.render(title, True, ui.BRIGHT)
        self.screen.blit(t, (60, 36))
        pygame.draw.line(self.screen, ui.BORDER, (60, 90), (w - 60, 90), 1)
        panel = pygame.Rect(60, 104, w - 120, h - 160)
        pygame.draw.rect(self.screen, ui.BG_PANEL, panel, border_radius=8)
        font = self.fonts.cjk_small if self.tr.lang == "ja" else self.fonts.mono_small
        lines = ui.wrap_text(body, font, panel.width - 40)
        lh = font.get_linesize()
        visible = (panel.height - 30) // lh
        maxoff = max(0, len(lines) - visible)
        self.scrolloff = min(self.scrolloff, maxoff)
        y = panel.y + 16
        for line in lines[self.scrolloff:self.scrolloff + visible]:
            color = ui.FG
            stripped = line.strip()
            if stripped.endswith(":") and not stripped.startswith(("sudo", "ufw")):
                color = ui.CYAN
            elif any(stripped.startswith(c) for c in ("sudo ", "ufw ", "netstat", "tcpdump", "systemctl",
                                                      "ps ", "kill", "apt ", "sed ", "grep ", "find ", "cat ",
                                                      "ls", "crontab", "chmod", "redis", "nano", "sysctl",
                                                      "dpkg", "ss ", "tail", "xz", "lpadmin", "iptables")):
                color = ui.GREEN
            self.screen.blit(font.render(line, True, color), (panel.x + 20, y))
            y += lh
        if maxoff:
            bar = f"{int(self.scrolloff/maxoff*100) if maxoff else 100}%"
            self.screen.blit(self.fonts.ui_small.render(bar, True, ui.DIM), (panel.right - 50, panel.y + 6))
        self._footer(self._("train.scroll") + "   •   ←/→ lessons")

    def _draw_progress(self):
        self._header("prog.title", self._("prog.subtitle"))
        w, h = self.screen.get_size()
        done = self.save.completed_count()
        pct = int(done / LEVEL_COUNT * 100)
        lines = []
        lines.append((self._("prog.overall", done=done, total=LEVEL_COUNT, pct=pct), ui.AMBER))
        hints = sum(self.save.level(i)["hints"] for i in range(1, LEVEL_COUNT + 1))
        lines.append((self._("prog.playtime", time=self._fmt_hms(self.save.data["play_seconds"])), ui.FG))
        lines.append((self._("prog.hints", n=hints), ui.FG))
        lines.append((self._("prog.lessons", n=len(self.save.data["lessons_read"]), total=len(LESSONS)), ui.FG))
        y = 128
        for text, color in lines:
            self.screen.blit(self.fonts.ui.render(text, True, color), (60, y))
            y += 30
        # progress bar
        bar = pygame.Rect(60, y + 4, w - 120, 18)
        pygame.draw.rect(self.screen, ui.BG_PANEL, bar, border_radius=9)
        fill = pygame.Rect(bar.x, bar.y, int(bar.width * done / LEVEL_COUNT), bar.height)
        pygame.draw.rect(self.screen, ui.GREEN, fill, border_radius=9)
        pygame.draw.rect(self.screen, ui.BORDER, bar, 1, border_radius=9)
        y += 40
        # table
        headers = [self._("prog.col.level"), self._("prog.col.status"), self._("prog.col.best"),
                   self._("prog.col.when"), self._("prog.col.tries")]
        xs = [60, 420, 560, 700, 980]
        for hx, htext in zip(xs, headers):
            self.screen.blit(self.fonts.ui_small.render(htext, True, ui.CYAN), (hx, y))
        y += 26
        pygame.draw.line(self.screen, ui.BORDER, (60, y), (w - 60, y), 1)
        y += 6
        rows_area = h - 70 - y
        row_h = max(22, min(30, rows_area // LEVEL_COUNT))
        for i in range(1, LEVEL_COUNT + 1):
            lv = self.save.level(i)
            name = f"{i:02d} {self._(f'lvl.{i}.name')}"
            self.screen.blit(self.fonts.ui_small.render(name[:34], True, ui.FG), (xs[0], y))
            if lv["completed"]:
                st, sc = self._("common.completed"), ui.GREEN
            elif lv["attempts"]:
                st, sc = self._("common.open"), ui.AMBER
            else:
                st, sc = "—", ui.DIM
            self.screen.blit(self.fonts.ui_small.render(st, True, sc), (xs[1], y))
            self.screen.blit(self.fonts.ui_small.render(fmt_time(lv["best"]) if lv["best"] else "—", True, ui.AMBER), (xs[2], y))
            self.screen.blit(self.fonts.ui_small.render(lv["completed_at"] or "—", True, ui.DIM), (xs[3], y))
            self.screen.blit(self.fonts.ui_small.render(str(lv["attempts"]), True, ui.FG), (xs[4], y))
            y += row_h
        self._footer(self._("prog.skills"))

    def _draw_records(self):
        self._header("rec.title")
        w, h = self.screen.get_size()
        n = self.rec_level
        name = f"{self._('sel.level')} {n}: {self._(f'lvl.{n}.name')}"
        self.screen.blit(self.fonts.h2.render(name, True, ui.GREEN), (60, 118))
        tag = " / ".join(ALL_LEVELS[n - 1].threat_tags)
        self.screen.blit(self.fonts.ui_small.render(tag, True, ui.CYAN), (62, 160))
        records = self.save.records(n)
        y = 206
        headers = [self._("rec.rank"), self._("rec.name"), self._("rec.time"), self._("rec.date")]
        xs = [80, 220, 560, 760]
        for hx, ht in zip(xs, headers):
            self.screen.blit(self.fonts.ui.render(ht, True, ui.CYAN), (hx, y))
        y += 32
        pygame.draw.line(self.screen, ui.BORDER, (60, y), (w - 60, y), 1)
        y += 10
        if not records:
            self.screen.blit(self.fonts.ui.render(self._("common.none_yet"), True, ui.DIM), (80, y + 20))
        for i, rec in enumerate(records):
            medal = ["①", "②", "③"][i] if i < 3 else f"{i+1}."
            color = ui.AMBER if i == 0 else (ui.BRIGHT if i < 3 else ui.FG)
            self.screen.blit(self.fonts.ui.render(medal, True, color), (xs[0], y))
            self.screen.blit(self.fonts.ui.render(rec["name"][:16], True, color), (xs[1], y))
            self.screen.blit(self.fonts.ui.render(fmt_time(rec["time"]), True, color), (xs[2], y))
            self.screen.blit(self.fonts.ui_small.render(rec["date"], True, ui.DIM), (xs[3], y + 2))
            y += 40
        self._footer(self._("rec.pick"))
        self._toggles_hint()

    def _draw_credits(self):
        self._header("cred.title")
        w, h = self.screen.get_size()
        y = 150
        for label_key, value, color in CREDITS(self.tr, __version__):
            if label_key:
                lab = self.fonts.ui.render(self._(label_key) + ":", True, ui.CYAN)
                self.screen.blit(lab, (120, y))
                val = self.fonts.ui.render(value, True, color)
                self.screen.blit(val, (360, y))
            else:
                val = self.fonts.ui.render(value, True, color)
                self.screen.blit(val, (w // 2 - val.get_width() // 2, y))
            y += 40
        self._footer(self._("menu.back") + ": Esc")

    def _draw_settings(self):
        self._header("menu.settings")
        w, h = self.screen.get_size()
        items = [
            ("lang", self._("set.lang"), self.tr("lang.name")),
            ("bgm", self._("set.bgm"), self._("common.on") if self.audio.bgm_on else self._("common.off")),
            ("sfx", self._("set.sfx"), self._("common.on") if self.audio.sfx_on else self._("common.off")),
            ("fullscreen", self._("set.fullscreen"), self._("common.on") if self.fullscreen else self._("common.off")),
            ("volume", self._("set.volume"), self._vol_bar()),
            ("reset", self._("set.reset"), ""),
        ]
        y = 170
        for i, (key, label, value) in enumerate(items):
            selected = i == self.sel_setting
            rect = pygame.Rect(120, y, w - 240, 50)
            if selected:
                pygame.draw.rect(self.screen, ui.SELECT_BG, rect, border_radius=6)
                pygame.draw.rect(self.screen, ui.GREEN, rect, 1, border_radius=6)
            self.screen.blit(self.fonts.ui.render(label, True, ui.BRIGHT if selected else ui.FG), (rect.x + 20, y + 10))
            if key == "reset" and self.reset_armed:
                value = self._("set.reset.confirm")
                vcolor = ui.RED
            else:
                vcolor = ui.AMBER
            vs = self.fonts.ui.render(value, True, vcolor)
            self.screen.blit(vs, (rect.right - vs.get_width() - 24, y + 10))
            if selected and key not in ("reset",):
                self.screen.blit(self.fonts.ui.render("‹", True, ui.GREEN), (rect.right - vs.get_width() - 48, y + 10))
                self.screen.blit(self.fonts.ui.render("›", True, ui.GREEN), (rect.right - 20, y + 10))
            y += 58
        self._footer(self._("menu.hint.nav"))

    def _vol_bar(self):
        filled = int(self.audio.volume * 10)
        return "█" * filled + "░" * (10 - filled)

    def _fmt_hms(self, seconds):
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h:
            return f"{h}h {m}m {s}s"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"


# ====================================================================== GameScene
class GameScene:
    def __init__(self, app, num):
        self.app = app
        self.num = num
        self.fonts = app.fonts
        self.tr = app.tr
        self.save = app.save
        self.world = build(World(seed=time.time_ns() & 0xFFFF))
        self.level = make_level(self.world, num)
        self.shell = Shell(self.world, self.tr, self.save, num)
        self.terminal = Terminal(self.fonts)
        self.terminal.on_submit = self.submit
        self.terminal.set_prompt(self.shell.prompt())
        self.remaining = float(LEVEL_TIME)
        self.state = "play"           # play / name / done / timeout
        self.editor = None
        self.win_time = None
        self.win_stamp = None
        self.rank = -1
        self.name_buf = self.save.data.get("last_name", "")
        self.exit_to_menu = False
        self.alert_flash = 0.0
        self.last_alert_count = len(self.world.alerts)
        self.play_accum = 0.0
        self._intro()

    def _intro(self):
        t = self.terminal
        t.write(self.tr("sh.welcome_hdr"), ui.AMBER)
        t.write("")
        node = self.world.fs.get("/home/player/welcome.txt")
        if node:
            for line in node.content.rstrip("\n").split("\n"):
                t.write(line, ui.FG)
        t.write("")
        t.write("=" * 56, ui.BORDER)
        res = self.shell.cmd_mission([], "")
        for line in res.out.rstrip("\n").split("\n"):
            t.write(line, ui.CYAN)
        t.write("=" * 56, ui.BORDER)
        t.write("")
        t.write(self.tr("sh.type_help"), ui.DIM)
        # surface the opening alerts
        for ts, sev, text in self.world.alerts[-3:]:
            t.write(f"[ALERT] {text}", ui.SEVERITY.get(sev, ui.RED))
        t.write("")

    # ------------------------------------------------------------------ input
    def on_key(self, event):
        if self.editor:
            self.editor.handle_key(event)
            if self.editor.result:
                kind, text = self.editor.result
                if kind == "save":
                    self._editor_save(text)
                    self.editor.result = None
                else:
                    self.editor = None
            return
        if self.state == "name":
            self._name_key(event)
            return
        if event.key == pygame.K_ESCAPE:
            if self.state in ("done", "timeout"):
                self.exit_to_menu = True
            else:
                # allow quick exit confirmation via 'menu'
                self.terminal.write(self.tr("game.quit"), ui.DIM)
            return
        res = self.terminal.handle_key(event, self.app.audio)
        if isinstance(res, tuple) and res and res[0] == "__TAB__":
            self._complete(res[1], res[2])

    def on_text(self, text):
        if self.editor:
            self.editor.handle_text(text)
        elif self.state == "name":
            if len(self.name_buf) < 16 and text.isprintable():
                self.name_buf += text
        elif self.state == "play":
            self.terminal.handle_text(text)

    def _name_key(self, event):
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            name = self.name_buf.strip() or "Anonymous"
            self.rank = self.save.add_record(self.num, name, self.win_time, self.win_stamp)
            self.app.audio.play("win")
            self.state = "done"
            self.terminal.write("")
            self.terminal.write(self.tr("game.win.saved"), ui.GREEN)
            self.terminal.write(self.tr("game.win.cont"), ui.DIM)
            self.terminal.enabled = True
        elif event.key == pygame.K_BACKSPACE:
            self.name_buf = self.name_buf[:-1]

    def submit(self, line):
        t = self.terminal
        t.write(self.shell.prompt() + line, ui.DIM)
        stripped = line.strip()
        if not stripped:
            return
        res = self.shell.run(line)
        if res.editor:
            kind, path, euser = res.editor
            node = self.world.fs.get(path)
            content = node.content if node else ""
            self.editor = NanoEditor(self.fonts, path, content)
            self._editor_target = path
            self._editor_user = euser
            return
        out = res.out
        if out == "__MENU__":
            self.exit_to_menu = True
            return
        if out == "__EXIT__":
            self.exit_to_menu = True
            return
        if out == "\x0c":
            t.clear()
        elif out:
            self._write_output(out, line)
        t.set_prompt(self.shell.prompt())
        if res.code != 0 and stripped.split()[0] not in ("grep", "false", "systemctl"):
            self.app.audio.play("error")
        else:
            self.app.audio.play("key")
        self._check_win()

    def _write_output(self, out, line):
        """Write command output, colourising a few well-known formats."""
        t = self.terminal
        cmd = line.strip().split()[0] if line.strip() else ""
        for raw in out.rstrip("\n").split("\n"):
            color = ui.FG
            low = raw.lower()
            if "[alert]" in low or "permission denied" in low or "denied" in low or "not found" in low or raw.startswith("rm:") or raw.startswith("cd:"):
                color = ui.RED
            elif "[x]" in raw or raw.strip().startswith("✓") or "active (running)" in raw or "OK" == raw.strip():
                color = ui.GREEN
            elif "[ ]" in raw:
                color = ui.DIM
            elif cmd == "tcpdump" and (">" in raw and "IP" in raw):
                color = ui.CYAN if "attack" not in raw else ui.AMBER
            elif "LISTEN" in raw:
                color = ui.CYAN
            elif raw.startswith("===") or raw.startswith("---"):
                color = ui.BORDER
            elif "Failed password" in raw or "UNION SELECT" in raw or "xmrig" in raw or "backdoor" in raw.lower():
                color = ui.AMBER
            t.write(raw, color)

    def _complete(self, text, cursor):
        """Simple tab completion for commands and paths."""
        from .system import COMMANDS
        prefix = text[:cursor]
        parts = prefix.split()
        if len(parts) <= 1 and not prefix.endswith(" "):
            cands = [c for c in COMMANDS if c.startswith(parts[0] if parts else "")]
            if len(cands) == 1:
                self.terminal.set_input(cands[0] + " " + text[cursor:])
            elif len(cands) > 1:
                self.terminal.write("  ".join(cands), ui.DIM)
        else:
            frag = parts[-1] if not prefix.endswith(" ") else ""
            import posixpath
            base = self.shell.abspath(posixpath.dirname(frag) or ".")
            node = self.world.fs.get(base)
            if node and node.is_dir:
                names = [n for n in node.children if n.startswith(posixpath.basename(frag))]
                if len(names) == 1:
                    child = node.children[names[0]]
                    completed = posixpath.join(posixpath.dirname(frag), names[0]) if posixpath.dirname(frag) else names[0]
                    newtext = " ".join(parts[:-1] + [completed]) + ("/" if child.is_dir else " ")
                    self.terminal.set_input(newtext)
                elif len(names) > 1:
                    self.terminal.write("  ".join(names), ui.DIM)

    def _editor_save(self, text):
        path = self._editor_target
        euser = getattr(self, "_editor_user", self.shell.user)
        groups = self.shell.groups_map.get(euser, [euser])
        node = self.world.fs.get(path)
        if node and euser != "root" and not self.world.fs.can(node, euser, groups, 2):
            self.terminal.write(f"nano: {path}: Permission denied (try: sudo nano {path})", ui.RED)
            return
        try:
            self.world.fs.write(path, text, owner=euser if not node else None)
            # editing a service config marks it needing restart
            self._mark_conf_dirty(path)
        except Exception as e:
            self.terminal.write(f"nano: {e}", ui.RED)

    def _mark_conf_dirty(self, path):
        w = self.world
        if path == "/etc/ssh/sshd_config":
            svc = w.service("ssh")
            if svc:
                svc.needs_restart = True
        elif path == "/etc/redis/redis.conf":
            svc = w.service("redis")
            if svc:
                svc.needs_restart = True
        elif path == "/etc/mysql/my.cnf":
            svc = w.service("mysql")
            if svc:
                svc.needs_restart = True

    # ------------------------------------------------------------------ update
    def update(self, dt):
        self.terminal.update(dt)
        if self.state == "play":
            self.remaining -= dt
            self.play_accum += dt
            if self.play_accum >= 1.0:
                self.save.add_play_time(self.play_accum)
                self.play_accum = 0.0
            self.world.time += dt
            self.level.tick(dt)
            if len(self.world.alerts) > self.last_alert_count:
                self.last_alert_count = len(self.world.alerts)
                self.app.audio.play("alert")
                self.alert_flash = 0.6
                ts, sev, text = self.world.alerts[-1]
                self.terminal.write(f"[ALERT] {text}", ui.SEVERITY.get(sev, ui.RED))
            if self.alert_flash > 0:
                self.alert_flash -= dt
            self._check_win()
            if self.remaining <= 0:
                self._timeout()

    def _check_win(self):
        if self.state != "play":
            return
        if self.level.solved():
            self.win_time = LEVEL_TIME - self.remaining
            self.win_stamp = self.save.complete(self.num, self.win_time)
            self.state = "name" if self.save.qualifies(self.num, self.win_time) else "done"
            self.app.audio.play("win")
            self._announce_win()

    def _announce_win(self):
        t = self.terminal
        t.write("")
        t.write(self.tr("game.win.title"), ui.GREEN)
        date = time.strftime("%Y-%m-%d %H:%M:%S")
        t.write(self.tr("game.win.time", time=fmt_time(self.win_time), date=self.win_stamp), ui.BRIGHT)
        if self.state == "name":
            t.write("")
            t.write(self.tr("game.win.record", rank="?"), ui.AMBER)
            t.enabled = False
        else:
            t.write(self.tr("game.win.cont"), ui.DIM)

    def _timeout(self):
        self.state = "timeout"
        self.terminal.write("")
        self.terminal.write("*** TIME UP - the server was overrun. Press Esc to return. ***", ui.RED)
        self.terminal.enabled = False
        self.app.audio.play("error")

    # ------------------------------------------------------------------ draw
    def draw(self, surface):
        surface.fill(ui.BG)
        w, h = surface.get_size()
        hud_h = 86
        hud = pygame.Rect(0, 0, w, hud_h)
        self._draw_hud(surface, hud)
        side_w = min(360, int(w * 0.32))
        term_rect = pygame.Rect(0, hud_h, w - side_w, h - hud_h)
        side_rect = pygame.Rect(w - side_w, hud_h, side_w, h - hud_h)
        if self.editor:
            self.editor.draw(surface, pygame.Rect(0, hud_h, w, h - hud_h))
        else:
            self.terminal.draw(surface, term_rect, show_input=(self.state == "play"))
            self._draw_side(surface, side_rect)
            if self.state == "name":
                self._draw_name_prompt(surface, term_rect)
        ui.draw_scanlines(surface, 10)

    def _draw_hud(self, surface, rect):
        pygame.draw.rect(surface, ui.BG_PANEL, rect)
        pygame.draw.line(surface, ui.BORDER, (0, rect.bottom), (rect.right, rect.bottom), 1)
        f = self.fonts
        # clock
        mins = int(self.remaining // 60)
        secs = int(self.remaining % 60)
        clock_color = ui.GREEN if self.remaining > 600 else (ui.AMBER if self.remaining > 120 else ui.RED)
        ctext = f"{mins:02d}:{secs:02d}"
        clabel = f.ui_small.render(self.tr("hud.time"), True, ui.DIM)
        surface.blit(clabel, (24, 12))
        csurf = f.h2.render(ctext, True, clock_color)
        surface.blit(csurf, (24, 30))
        # level name
        lvl = f.ui_small.render(f"{self.tr('hud.level')} {self.num}", True, ui.DIM)
        surface.blit(lvl, (170, 12))
        name = f.ui_bold.render(self.tr(f"lvl.{self.num}.name"), True, ui.BRIGHT)
        surface.blit(name, (170, 30))
        # meters
        self._meter(surface, rect.right - 420, 20, self.tr("hud.load"), min(1.0, self.world.load / 10), ui.RED if self.world.load > 5 else ui.GREEN)
        self._meter(surface, rect.right - 420, 48, self.tr("hud.net"), min(1.0, self.world.netload), ui.AMBER if self.world.netload > 0.6 else ui.CYAN)
        # completed badge
        if self.state in ("done", "name"):
            badge = f.ui_bold.render("✓ " + self.tr("hud.secured"), True, ui.GREEN)
            surface.blit(badge, (rect.right - badge.get_width() - 24, 48))
        elif self.alert_flash > 0 and int(self.alert_flash * 10) % 2 == 0:
            badge = f.ui_bold.render("⚠ UNDER ATTACK", True, ui.RED)
            surface.blit(badge, (rect.centerx - badge.get_width() // 2, 14))

    def _meter(self, surface, x, y, label, frac, color):
        f = self.fonts
        lab = f.ui_small.render(label, True, ui.DIM)
        surface.blit(lab, (x, y))
        bar = pygame.Rect(x + 60, y + 4, 180, 12)
        pygame.draw.rect(surface, ui.BG, bar, border_radius=6)
        fill = pygame.Rect(bar.x, bar.y, int(bar.width * frac), bar.height)
        pygame.draw.rect(surface, color, fill, border_radius=6)
        pygame.draw.rect(surface, ui.BORDER, bar, 1, border_radius=6)

    def _draw_side(self, surface, rect):
        pygame.draw.rect(surface, ui.BG_PANEL, rect)
        pygame.draw.line(surface, ui.BORDER, (rect.x, rect.y), (rect.x, rect.bottom), 1)
        f = self.fonts
        pad = 16
        y = rect.y + pad
        title = f.ui_bold.render(self.tr("hud.objectives"), True, ui.CYAN)
        surface.blit(title, (rect.x + pad, y))
        y += title.get_height() + 10
        for done, key in self.level.objectives():
            mark = "☑" if done else "☐"
            color = ui.GREEN if done else ui.FG
            text = self.tr(key)
            lines = ui.wrap_text(text, f.ui_small, rect.width - pad * 2 - 24)
            surface.blit(f.ui.render(mark, True, color), (rect.x + pad, y))
            for j, ln in enumerate(lines):
                surface.blit(f.ui_small.render(ln, True, color), (rect.x + pad + 26, y + j * f.small_line_h))
            y += max(f.line_h, len(lines) * f.small_line_h) + 8
        # progress fraction
        done_n = sum(1 for d, _ in self.level.objectives() if d)
        total = len(self.level.objectives())
        y += 4
        pygame.draw.line(surface, ui.BORDER, (rect.x + pad, y), (rect.right - pad, y), 1)
        y += 10
        frac_text = f"{done_n}/{total}"
        surface.blit(f.ui.render(frac_text, True, ui.AMBER), (rect.x + pad, y))
        y += 40
        # recent alerts / hint helper
        htitle = f.ui_small.render("ALERTS", True, ui.DIM)
        surface.blit(htitle, (rect.x + pad, y))
        y += 22
        for ts, sev, text in self.world.alerts[-4:]:
            lines = ui.wrap_text("• " + text, f.ui_small, rect.width - pad * 2)
            for ln in lines:
                if y > rect.bottom - 60:
                    break
                surface.blit(f.ui_small.render(ln, True, ui.SEVERITY.get(sev, ui.FG)), (rect.x + pad, y))
                y += f.small_line_h
            y += 4
        tip = f.ui_small.render("Type 'hint' for help", True, ui.DIM)
        surface.blit(tip, (rect.x + pad, rect.bottom - 30))

    def _draw_name_prompt(self, surface, rect):
        w = min(560, rect.width - 60)
        box = pygame.Rect(rect.centerx - w // 2, rect.centery - 70, w, 150)
        pygame.draw.rect(surface, ui.BG_PANEL, box, border_radius=10)
        pygame.draw.rect(surface, ui.GREEN, box, 2, border_radius=10)
        f = self.fonts
        title = f.ui_bold.render(self.tr("game.win.record", rank="TOP 10"), True, ui.AMBER)
        surface.blit(title, (box.centerx - title.get_width() // 2, box.y + 16))
        prompt = f.ui.render(self.tr("game.win.name"), True, ui.FG)
        surface.blit(prompt, (box.x + 24, box.y + 64))
        field = pygame.Rect(box.x + 24, box.y + 96, box.width - 48, 36)
        pygame.draw.rect(surface, ui.BG_INPUT, field, border_radius=6)
        pygame.draw.rect(surface, ui.BORDER, field, 1, border_radius=6)
        nfont = f.cjk if ui.has_cjk(self.name_buf) else f.mono
        nsurf = nfont.render(self.name_buf, True, ui.BRIGHT)
        surface.blit(nsurf, (field.x + 10, field.y + 6))
        if int(self.app.anim * 2) % 2 == 0:
            cx = field.x + 10 + nsurf.get_width()
            pygame.draw.rect(surface, ui.GREEN, (cx, field.y + 6, 10, 24))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="CyberDefence")
    parser.add_argument("--smoke-test", metavar="FILE", help="boot headless, write a status line, exit")
    parser.add_argument("--version", action="store_true")
    args = parser.parse_args()
    if args.version:
        print(f"CyberDefence v{__version__}")
        return 0
    if args.smoke_test:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    app = App(smoke=args.smoke_test)
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
