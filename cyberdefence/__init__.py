"""CyberDefence - a terminal cyber attack defence simulator."""
__version__ = "0.1.1"
__title__ = "CyberDefence"

# True when running in a web browser (pygbag / WebAssembly).
import sys as _sys
WEB = _sys.platform == "emscripten"
