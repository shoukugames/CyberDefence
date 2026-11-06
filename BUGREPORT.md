# Reporting a bug in CyberDefence

Thanks for helping make CyberDefence better! Please report bugs by email to
**info@shoukugames.org** (or via <https://shoukugames.org/>), with as much of the
information below as you can.

## Before you report

- Make sure you are on the latest version (**current: v0.1.1** — shown on the
  title screen and in the Credits section).
- Check whether the problem happens every time, or only sometimes.

## What to include

1. **Version** — e.g. `v0.1.1` (title screen, bottom corner).
2. **Platform** — Windows / Linux, and how you installed it (`.deb`, `.exe`, or
   from source).
3. **Language** — were you in English or 日本語?
4. **Where it happened** — which menu or which level (number and name).
5. **What you did** — the exact commands you typed in the terminal, in order, if
   the bug was in a level.
6. **What you expected** vs. **what actually happened.**
7. **Screenshot**, if the problem is visual.

### A good example

```
Version:  v0.1.1
Platform: Linux (.deb)
Language: English
Where:    Level 6 - Exposed Redis RCE
Steps:    sudo ufw enable
          sudo ufw deny 6379/tcp
Expected: the "Stop Redis facing the Internet" objective to tick off
Actual:   it stayed unchecked even though netstat showed the port blocked
```

## Save data & logs

Your progress is stored in a single `save.json`:

- **Linux:** `~/.local/share/cyberdefence/save.json`
- **Windows:** `%APPDATA%\CyberDefence\save.json`

If the game won't start or your progress looks wrong, attaching this file helps a
lot. You can also move it aside to start fresh (the game writes a new one).

## Security note

CyberDefence is a self-contained **simulation** — it never touches a real network,
filesystem outside its save file, or any live service. If you believe you've found
a real security issue in the program itself (not in the simulated scenarios),
please mark your email **SECURITY** so we can prioritise it.
