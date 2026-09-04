"""
brain.py
--------
Azuki's voice. Wraps a single Claude call with Azuki's personality system
prompt, plus a small offline bank of idle mutters so the companion feels
alive without hitting the API for every little animation beat — the API
is only called when the user actually types something to Azuki.
"""

import random

from . import config

# A short rolling window of conversation so replies have a little
# continuity without the context growing unbounded on a desktop widget.
_MAX_HISTORY_TURNS = 6

# Idle chatter Azuki can say on its own, with zero API calls — shown at
# random while wandering, or if the API key isn't configured at all.
IDLE_MUTTERS = [
    "hmm...",
    "*stretches*",
    "ooh, what's over there?",
    "this pixel looks comfy.",
    "la la la~",
    "is it snack time yet?",
    "just vibing.",
    "the cursor went zoom.",
    "i could nap right here.",
    "wonder what's in that window.",
]

# Reactions to being clicked/petted/dragged — also free, no API call.
POKE_REACTIONS = ["hehe!", "hey!", "that tickles.", "wheee!", "eep!", "again, again!"]
DRAG_REACTIONS = ["whoaaa!", "flying!", "put me down— just kidding, keep going.", "wheee!"]


class AzukiBrain:
    """Lazily creates the Anthropic client on first real chat message, so
    the companion still runs (wandering, reacting to clicks) with zero
    setup if ANTHROPIC_API_KEY isn't set — it just won't hold a real
    conversation until you add one."""

    def __init__(self) -> None:
        self._client = None
        self.history: list[dict] = []

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not config.ANTHROPIC_API_KEY:
            return None
        from anthropic import Anthropic

        self._client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
        return self._client

    def has_api_access(self) -> bool:
        return bool(config.ANTHROPIC_API_KEY)

    def idle_mutter(self) -> str:
        return random.choice(IDLE_MUTTERS)

    def poke_reaction(self) -> str:
        return random.choice(POKE_REACTIONS)

    def drag_reaction(self) -> str:
        return random.choice(DRAG_REACTIONS)

    def reply(self, user_message: str) -> str:
        """Get Azuki's in-character reply to something the user typed.
        Falls back to a canned line if no API key is configured, so the
        UI never has to special-case a missing key."""
        client = self._ensure_client()
        if client is None:
            return "i can't really chat yet — ask whoever set me up to add an ANTHROPIC_API_KEY!"

        self.history.append({"role": "user", "content": user_message})
        self.history = self.history[-(_MAX_HISTORY_TURNS * 2):]

        try:
            response = client.messages.create(
                model=config.CHAT_MODEL,
                max_tokens=config.MAX_TOKENS,
                system=config.AZUKI_SYSTEM_PROMPT,
                messages=self.history,
            )
        except Exception:  # noqa: BLE001 - a desktop pet should never crash on a network hiccup
            return "hmm, i got a little dizzy there — try again?"

        text = "".join(block.text for block in response.content if block.type == "text").strip()
        if not text:
            text = self.idle_mutter()

        self.history.append({"role": "assistant", "content": text})
        return text

    def reset(self) -> None:
        self.history = []
