"""
AZUKI — a portable, desktop-traversing AI companion.

A tiny always-on-top creature that lives on your screen, wanders along
your desktop's edges (crossing between monitors just like a real virtual
desktop), and can be poked, dragged, and talked to via Claude.

    from azuki import AzukiWindow, AzukiBrain, Movement

See README.md for setup and usage.
"""

from .brain import AzukiBrain
from .movement import Movement, MovementState
from .ui import AzukiWindow

__all__ = ["AzukiBrain", "Movement", "MovementState", "AzukiWindow"]
__version__ = "0.1.0"
