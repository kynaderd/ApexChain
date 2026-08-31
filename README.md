# AZUKI

**Azuki** is a portable, desktop-traversing AI companion — a tiny,
always-on-top creature that lives on your screen, wanders along the
edges of your monitors (crossing between them like they're one
continuous desktop, because they are), and can be poked, dragged, and
talked to via Claude.

No external image assets, no cloud backend required to run — the
creature itself is drawn with vector shapes, and it wanders and reacts
to clicks/drags with zero setup. Add an Anthropic API key and it can
actually talk back. 

## Features 

- **Always-on-top, transparent, borderless** — sits on top of every
  other window without a taskbar entry.
- **Desktop-traversing movement** — treats every connected monitor as
  one shared coordinate space, falls to the nearest "ground" (the
  bottom edge of whatever screen it's over), and wanders left/right or
  occasionally makes a longer trip to a distant point on the desktop —
  which, if your monitors are arranged side by side, means it genuinely
  walks from one screen to the next.
- **Physics-lite**: gravity, idle "breathing" bob, and a little
  "throw" when you drag-release it.
- **Click-to-react**: hovering, clicking, and dragging all get
  in-character reactions.
- **Double-click (or tray menu) to chat** — opens a text prompt and
  Azuki replies in a speech bubble, in character, via Claude.
- **Click-through mode** — toggle from the tray icon so Azuki stops
  intercepting clicks meant for whatever's underneath it.
- **Works without an API key** — idle mutters, poke/drag reactions, and
  wandering are all free, local, and instant; only typed conversation
  needs `ANTHROPIC_API_KEY`.

## Files

| File | Purpose |
|---|---|
| `main.py` | Entry point — creates the Qt app and Azuki's window |
| `azuki/__init__.py` | Package exports (`AzukiWindow`, `AzukiBrain`, `Movement`) |
| `azuki/config.py` | Env vars, model selection, personality prompt, physics/render constants |
| `azuki/movement.py` | Toolkit-independent physics/state machine (gravity, walking, cross-monitor traversal) |
| `azuki/brain.py` | Claude-backed personality/chat, plus free offline idle chatter |
| `azuki/ui.py` | PySide6 window: sprite rendering, mouse interactions, tray icon, speech bubble |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Standard Python/OS/IDE ignores |
| `LICENSE` | MIT license |
| `README.md` | This file |

## Setup

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **(Optional) set your Anthropic API key**, so Azuki can actually
   chat back instead of just wandering and reacting:

   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

   Get a key at <https://console.anthropic.com/>. Without this set,
   Azuki still runs fine — double-clicking it to chat will just tell
   you a key hasn't been configured yet.

3. **(Optional) tune the model or personality budget**

   ```bash
   export AZUKI_MODEL="claude-sonnet-5"   # default
   export AZUKI_MAX_TOKENS=120            # default — keeps replies bubble-sized
   ```

## Running it

```bash
python main.py
```

Azuki spawns near the top-left of your primary display, falls to the
nearest screen edge, and starts wandering. A tray icon appears with:

- **Talk to Azuki...** — opens a text prompt; Azuki replies in a speech
  bubble.
- **Click-through mode** — toggle so clicks pass through Azuki to
  whatever's underneath.
- **Reset conversation** — clears Azuki's chat memory (its wandering
  and reactions are unaffected).
- **Quit Azuki**.

You can also:

- **Click and drag** Azuki anywhere — release mid-swipe to give it a
  little throw, and gravity will settle it onto the nearest screen
  edge.
- **Hover over it** for a quick in-character reaction.
- **Double-click it** as a shortcut to the chat prompt.

## How the traversal works

`azuki/movement.py` has no Qt dependency at all — it just tracks a
position and a small state machine (`IDLE`, `WALK_LEFT`, `WALK_RIGHT`,
`FALLING`, `DRAGGING`, `TRAVERSING`, `TALKING`) over a list of monitor
rectangles you feed it. Each tick:

1. It finds the "ground" below Azuki's current x — the bottom edge of
   whichever monitor's horizontal range contains it.
2. If Azuki isn't resting on that ground, gravity pulls it down until
   it lands.
3. Once grounded, a short randomized timer decides whether Azuki idles,
   walks a direction for a while, or — occasionally — starts
   `TRAVERSING` toward a random point across the *entire* virtual
   desktop, which is what carries it across monitor boundaries over
   time.

`azuki/ui.py` just reads `.x`, `.y`, `.bob_offset`, and `.state` off a
`Movement` instance every 33ms, repositions the (otherwise invisible)
window, and repaints the creature — so swapping in a sprite-sheet
animation later wouldn't require touching the physics code at all.

## Extending Azuki

- **Give it a real sprite sheet**: replace `_paint_bean()` in
  `azuki/ui.py` with `QPixmap` frame-blitting; `Movement.state` already
  tells you which animation to play.
- **Add sound**: hook `AzukiWindow._say()` in `azuki/ui.py` up to
  `QSoundEffect` for a little chirp per reaction.
- **Change its personality**: edit `AZUKI_SYSTEM_PROMPT` in
  `azuki/config.py` — it's the only place Azuki's voice is defined.
- **Persist memory across restarts**: `AzukiBrain.history` in
  `azuki/brain.py` is in-memory only today; serialize it to disk on
  `reset()`/exit if you want Azuki to remember past conversations.
