"""Locations of bundled assets and per-user save data."""
import os
import sys


def asset_dir():
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, "assets")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def asset(*parts):
    return os.path.join(asset_dir(), *parts)


def data_dir():
    override = os.environ.get("CYBERDEFENCE_DATA")
    if override:
        path = override
    elif sys.platform == "win32":
        path = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "CyberDefence")
    else:
        root = os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share"))
        path = os.path.join(root, "cyberdefence")
    os.makedirs(path, exist_ok=True)
    return path
