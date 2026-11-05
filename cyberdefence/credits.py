"""Credits screen content."""
import datetime

from . import ui

WEBSITE = "https://shoukugames.org/"
EMAIL = "info@shoukugames.org"
RELEASE_DATE = "2026-11-06"


def CREDITS(tr, version):
    """Return a list of (label_key_or_None, value, color) rows."""
    rows = [
        (None, "CyberDefence", ui.GREEN),
        (None, tr("app.tagline"), ui.CYAN),
        (None, "", ui.FG),
        ("cred.created", "Shawn Rapaz", ui.BRIGHT),
        ("cred.with", "Claude Code", ui.BRIGHT),
        ("cred.version", f"v{version}", ui.AMBER),
        ("cred.date", RELEASE_DATE, ui.FG),
        ("cred.web", WEBSITE, ui.BLUE),
        ("cred.email", EMAIL, ui.BLUE),
        ("cred.license", "GNU GPL v3.0", ui.FG),
        (None, "", ui.FG),
        (None, tr("cred.ages"), ui.AMBER),
        (None, "", ui.FG),
        (None, tr("cred.thanks"), ui.GREEN),
    ]
    return rows
