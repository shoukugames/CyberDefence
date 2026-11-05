"""Progress, Top 10 speed runs and settings, stored as JSON in the user's data folder."""
import json
import os
import time

from .paths import data_dir

LEVEL_COUNT = 10
TOP_N = 10


def _blank():
    return {
        "version": 1,
        "settings": {"lang": "en", "bgm": True, "sfx": True, "fullscreen": False},
        "last_name": "",
        "levels": {str(i): {"completed": False, "best": None, "completed_at": None,
                            "attempts": 0, "wins": 0, "hints": 0} for i in range(1, LEVEL_COUNT + 1)},
        "records": {str(i): [] for i in range(1, LEVEL_COUNT + 1)},
        "lessons_read": [],
        "play_seconds": 0.0,
        "first_played": None,
    }


class Save:
    def __init__(self, path=None):
        self.path = path or os.path.join(data_dir(), "save.json")
        self.data = _blank()
        self.load()

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as fh:
                loaded = json.load(fh)
        except (OSError, ValueError):
            return
        blank = _blank()
        for key, value in loaded.items():
            if isinstance(blank.get(key), dict) and isinstance(value, dict):
                blank[key].update(value)
            else:
                blank[key] = value
        self.data = blank

    def write(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self.data, fh, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
        except OSError:
            pass

    # settings -----------------------------------------------------------
    @property
    def settings(self):
        return self.data["settings"]

    def set(self, key, value):
        self.data["settings"][key] = value
        self.write()

    # progress -----------------------------------------------------------
    def level(self, n):
        return self.data["levels"][str(n)]

    def start_attempt(self, n):
        lv = self.level(n)
        lv["attempts"] += 1
        if not self.data["first_played"]:
            self.data["first_played"] = time.strftime("%Y-%m-%d %H:%M")
        self.write()

    def add_play_time(self, seconds):
        self.data["play_seconds"] += seconds

    def add_hint(self, n):
        self.level(n)["hints"] += 1

    def complete(self, n, elapsed):
        """Mark a level won. Returns the completion timestamp string."""
        lv = self.level(n)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        lv["completed"] = True
        lv["wins"] += 1
        if lv["best"] is None or elapsed < lv["best"]:
            lv["best"] = elapsed
            lv["completed_at"] = stamp
        self.write()
        return stamp

    def completed_count(self):
        return sum(1 for i in range(1, LEVEL_COUNT + 1) if self.level(i)["completed"])

    # records ------------------------------------------------------------
    def records(self, n):
        return self.data["records"][str(n)]

    def qualifies(self, n, elapsed):
        recs = self.records(n)
        return len(recs) < TOP_N or elapsed < recs[-1]["time"]

    def add_record(self, n, name, elapsed, stamp):
        recs = self.records(n)
        entry = {"name": name[:16] or "???", "time": elapsed, "date": stamp}
        recs.append(entry)
        recs.sort(key=lambda r: r["time"])
        del recs[TOP_N:]
        self.data["last_name"] = name[:16]
        self.write()
        return recs.index(entry) if entry in recs else -1

    def mark_lesson(self, key):
        if key not in self.data["lessons_read"]:
            self.data["lessons_read"].append(key)
            self.write()


def fmt_time(seconds):
    if seconds is None:
        return "--:--.-"
    seconds = max(0.0, seconds)
    m, s = divmod(seconds, 60)
    return f"{int(m):02d}:{s:04.1f}"
