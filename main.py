#!/usr/bin/env python3
"""
main.py
-------
Launches Azuki: a single always-on-top window that lives on top of your
desktop, wanders along your screens' edges, and reacts when you click,
drag, or talk to it.

Usage:
    python main.py

Requires ANTHROPIC_API_KEY to be set in your environment for Azuki to
hold real conversations (see README.md) — without it, Azuki still
wanders and reacts to clicks/drags, it just can't chat back.
"""

import sys

from PySide6.QtWidgets import QApplication

from azuki import AzukiWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # keep running via the tray icon even if the window is hidden

    azuki = AzukiWindow()
    azuki.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
