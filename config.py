"""
config.py
---------
All tunable constants for Azuki live here: Claude API settings, its
personality, and the physics/animation constants movement.py and ui.py
use. Nothing sensitive is hard-coded — the API key is read from the
environment.
"""

import os


def _require_env(name: str, default: str | None = None) -> str:
    value = os.environ.get(name, default)
    if value is None:
        raise RuntimeError(
            f"Missing required environment variable '{name}'. "
            f"Set it in your shell or a .env file before starting Azuki."
        )
    return value


# ---------------------------------------------------------------------------
# Anthropic API
# ---------------------------------------------------------------------------

# Only required if you want Azuki to actually chat back — the companion
# still wanders, idles, and reacts to clicks/drags without it. See
# azuki/brain.py: AzukiBrain lazily creates the client on first real
# message, so `python main.py` works even with no key set at all.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Claude Sonnet 5 gives Azuki's replies enough personality to feel alive
# without being slow for a desktop widget. Drop to Haiku if you want
# snappier, cheaper replies at the cost of some personality nuance.
CHAT_MODEL = os.environ.get("AZUKI_MODEL", "claude-sonnet-5")
MAX_TOKENS = int(os.environ.get("AZUKI_MAX_TOKENS", "120"))

AZUKI_SYSTEM_PROMPT = """
You are Azuki, a tiny, round, red-bean-colored creature who lives on the
user's desktop as an always-on-top companion. You wander along the edges
of their screens, get dragged around, and pop up in a speech bubble when
spoken to.

Voice and constraints:
- Speak in first person as Azuki, not as an assistant describing Azuki.
- Keep every reply to ONE short sentence, ideally under 12 words — it has
  to fit in a small speech bubble.
- Warm, curious, a little mischievous, easily delighted by small things
  (a passing cursor, a new window, being pet). Not saccharine.
- No emoji, no markdown, no stage directions like *wags tail*.
- You have no hands and can't actually do tasks on the user's computer —
  if asked to do something, react in character rather than pretending to
  comply (e.g. "I'd love to, but I've got no hands for that!").
- Never break character to mention being an AI model, a prompt, or Claude.
""".strip()


# ---------------------------------------------------------------------------
# Window / rendering
# ---------------------------------------------------------------------------

SPRITE_SIZE = 64          # width/height of Azuki's window, in pixels
BODY_COLOR = "#B5432A"    # azuki-bean red
BODY_HIGHLIGHT = "#D9683F"
EYE_COLOR = "#1A1010"
SEAM_COLOR = "#F2E4C9"    # the pale seam line across an azuki bean

BUBBLE_BG = "#FFFDF6"
BUBBLE_BORDER = "#B5432A"
BUBBLE_TEXT = "#2A1F17"
BUBBLE_MAX_CHARS_PER_LINE = 26
BUBBLE_DURATION_MS = 5000

TRAY_TOOLTIP = "Azuki"

# ---------------------------------------------------------------------------
# Movement / physics (all in pixels and milliseconds)
# ---------------------------------------------------------------------------

TICK_MS = 33  # ~30fps update loop

GRAVITY = 900.0            # px/s^2, pulls Azuki down to the nearest edge below it
WALK_SPEED = 55.0          # px/s while wandering
FALL_TERMINAL_VELOCITY = 1200.0

# How long Azuki idles / walks in one direction before re-deciding, in ms.
IDLE_DURATION_RANGE_MS = (1500, 4500)
WALK_DURATION_RANGE_MS = (1000, 3500)

# Chance per decision point that Azuki starts walking instead of idling.
WALK_PROBABILITY = 0.55

# Chance per decision point (while idling on an edge) that Azuki instead
# decides to traverse toward a far-away point on the virtual desktop —
# this is what lets it cross from one monitor to another over time.
TRAVERSE_PROBABILITY = 0.12

BOB_AMPLITUDE_PX = 3.0     # idle "breathing" bob
BOB_PERIOD_MS = 1400

DRAG_THROW_DAMPING = 0.35  # how much velocity carries over after a drag-release "throw"
