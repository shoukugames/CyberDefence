"""Background music and sound effects, with on/off toggles."""
import os

import pygame

from .paths import asset_dir


def _find(name):
    base = os.path.join(asset_dir(), "audio")
    for ext in (".ogg", ".wav"):
        p = os.path.join(base, name + ext)
        if os.path.exists(p):
            return p
    return None


class Audio:
    def __init__(self, bgm=True, sfx=True, volume=0.6):
        self.bgm_on = bgm
        self.sfx_on = sfx
        self.volume = volume
        self.ok = False
        self.sounds = {}
        self._music = _find("ambient")
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self.ok = True
        except pygame.error:
            self.ok = False
        if self.ok:
            self._load_sfx()
            if self.bgm_on:
                self.start_music()

    def _load_sfx(self):
        for name in ("key", "select", "move", "error", "alert", "win"):
            path = _find(name)
            if path:
                try:
                    snd = pygame.mixer.Sound(path)
                    snd.set_volume(0.5)
                    self.sounds[name] = snd
                except pygame.error:
                    pass

    def start_music(self):
        if not self.ok or not self._music:
            return
        try:
            pygame.mixer.music.load(self._music)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play(-1, fade_ms=1500)
        except pygame.error:
            pass

    def stop_music(self):
        if self.ok:
            try:
                pygame.mixer.music.fadeout(600)
            except pygame.error:
                pass

    def set_bgm(self, on):
        self.bgm_on = on
        if on:
            self.start_music()
        else:
            self.stop_music()

    def toggle_bgm(self):
        self.set_bgm(not self.bgm_on)
        return self.bgm_on

    def set_volume(self, vol):
        self.volume = max(0.0, min(1.0, vol))
        if self.ok:
            try:
                pygame.mixer.music.set_volume(self.volume)
            except pygame.error:
                pass

    def play(self, name):
        if self.ok and self.sfx_on and name in self.sounds:
            try:
                self.sounds[name].play()
            except pygame.error:
                pass
