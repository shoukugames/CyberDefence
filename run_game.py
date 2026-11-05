#!/usr/bin/env python3
"""Launch CyberDefence from a source checkout (also the PyInstaller entry point)."""
from cyberdefence.app import main

if __name__ == "__main__":
    raise SystemExit(main())
