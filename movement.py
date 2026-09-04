"""
movement.py
-----------
Azuki's physics/behavior brain, deliberately kept independent of any GUI
toolkit so it can be unit tested (or reused with a different renderer)
without importing Qt.

The core idea behind "desktop-traversing": the virtual desktop is treated
as one coordinate space spanning every connected monitor (this is exactly
how a multi-monitor OS already lays out screen geometry). Azuki always
looks for the nearest "ground" — the bottom edge of whichever monitor sits
under its current x position — falls to it if it isn't already resting on
one, and wanders left/right along it. Because monitor geometries are laid
out edge-to-edge in that shared space, walking (or deliberately
"traversing" toward a distant point) naturally carries Azuki from one
screen onto the next.
"""

import math
import random
from dataclasses import dataclass
from enum import Enum, auto

from . import config


class MovementState(Enum):
    IDLE = auto()
    WALK_LEFT = auto()
    WALK_RIGHT = auto()
    FALLING = auto()
    DRAGGING = auto()
    TRAVERSING = auto()
    TALKING = auto()


@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def left(self) -> int:
        return self.x

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h


class Movement:
    """Owns Azuki's position and state machine. Call `update(dt_ms)` on a
    timer tick, and read `.x`, `.y`, `.bob_offset`, `.state` to render."""

    def __init__(self, x: float, y: float, sprite_size: int = config.SPRITE_SIZE):
        self.x = x
        self.y = y
        self.sprite_size = sprite_size
        self.velocity_x = 0.0
        self.velocity_y = 0.0

        self.state = MovementState.IDLE
        self._state_timer_ms = self._pick_duration(config.IDLE_DURATION_RANGE_MS)
        self._traverse_target_x: float | None = None
        self._elapsed_ms = 0.0

        self.screens: list[Rect] = [Rect(0, 0, 1920, 1080)]  # sane default, override via set_screens

    # -- setup ---------------------------------------------------------

    def set_screens(self, screens: list[tuple[int, int, int, int]]) -> None:
        """Feed in the current monitor layout as a list of
        (x, y, width, height) tuples in virtual-desktop coordinates —
        e.g. from `[s.geometry().getRect() for s in QGuiApplication.screens()]`.
        """
        if screens:
            self.screens = [Rect(*s) for s in screens]

    # -- queries ---------------------------------------------------------

    def center_x(self) -> float:
        return self.x + self.sprite_size / 2

    def virtual_bounds(self) -> Rect:
        """Bounding box of the whole multi-monitor desktop."""
        min_x = min(s.left for s in self.screens)
        min_y = min(s.y for s in self.screens)
        max_x = max(s.right for s in self.screens)
        max_y = max(s.bottom for s in self.screens)
        return Rect(min_x, min_y, max_x - min_x, max_y - min_y)

    def ground_y_below(self, x: float) -> float:
        """The y-coordinate of the nearest walkable ground at horizontal
        position `x` — the bottom edge of whichever monitor's x-range
        contains it. Falls back to the lowest monitor bottom overall if
        `x` sits in a gap between non-adjacent monitors."""
        candidates = [s.bottom for s in self.screens if s.left <= x < s.right]
        if candidates:
            return float(min(candidates))
        return float(max(s.bottom for s in self.screens))

    def is_grounded(self) -> bool:
        return abs((self.y + self.sprite_size) - self.ground_y_below(self.center_x())) < 1.0

    # -- external control (drag) -----------------------------------------

    def begin_drag(self) -> None:
        self.state = MovementState.DRAGGING
        self.velocity_x = 0.0
        self.velocity_y = 0.0

    def drag_to(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def end_drag(self, release_velocity_x: float = 0.0, release_velocity_y: float = 0.0) -> None:
        """Call when the user lets go, optionally with a recent drag
        velocity so releasing mid-swipe gives Azuki a little "throw"."""
        self.velocity_x = release_velocity_x * config.DRAG_THROW_DAMPING
        self.velocity_y = release_velocity_y * config.DRAG_THROW_DAMPING
        self.state = MovementState.FALLING  # gravity will resolve it onto the nearest ground

    def start_talking(self) -> None:
        """Pause wandering while a speech bubble is showing."""
        self.state = MovementState.TALKING
        self.velocity_x = 0.0

    def stop_talking(self) -> None:
        if self.state == MovementState.TALKING:
            self.state = MovementState.IDLE
            self._state_timer_ms = self._pick_duration(config.IDLE_DURATION_RANGE_MS)

    # -- main loop ---------------------------------------------------------

    def update(self, dt_ms: float) -> None:
        self._elapsed_ms += dt_ms

        if self.state in (MovementState.DRAGGING, MovementState.TALKING):
            return  # position/velocity managed externally while dragging or paused for speech

        dt = dt_ms / 1000.0
        ground_y = self.ground_y_below(self.center_x())
        grounded = abs((self.y + self.sprite_size) - ground_y) < 1.0 and self.state != MovementState.FALLING

        if not grounded:
            self._apply_gravity(dt, ground_y)
            return

        self._state_timer_ms -= dt_ms
        if self._state_timer_ms <= 0:
            self._decide_next_state()

        if self.state == MovementState.WALK_LEFT:
            self.x -= config.WALK_SPEED * dt
        elif self.state == MovementState.WALK_RIGHT:
            self.x += config.WALK_SPEED * dt
        elif self.state == MovementState.TRAVERSING and self._traverse_target_x is not None:
            direction = 1 if self._traverse_target_x > self.x else -1
            self.x += direction * config.WALK_SPEED * 1.4 * dt
            if abs(self.x - self._traverse_target_x) < 4:
                self._traverse_target_x = None
                self.state = MovementState.IDLE
                self._state_timer_ms = self._pick_duration(config.IDLE_DURATION_RANGE_MS)

        self._clamp_to_virtual_bounds()

    # -- internals ---------------------------------------------------------

    def _apply_gravity(self, dt: float, ground_y: float) -> None:
        self.state = MovementState.FALLING
        self.velocity_y = min(self.velocity_y + config.GRAVITY * dt, config.FALL_TERMINAL_VELOCITY)
        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt

        if self.y + self.sprite_size >= ground_y:
            self.y = ground_y - self.sprite_size
            self.velocity_x = 0.0
            self.velocity_y = 0.0
            self.state = MovementState.IDLE
            self._state_timer_ms = self._pick_duration(config.IDLE_DURATION_RANGE_MS)

        self._clamp_to_virtual_bounds()

    def _decide_next_state(self) -> None:
        roll = random.random()

        if roll < config.TRAVERSE_PROBABILITY:
            bounds = self.virtual_bounds()
            self._traverse_target_x = random.uniform(bounds.left + self.sprite_size, bounds.right - self.sprite_size)
            self.state = MovementState.TRAVERSING
            self._state_timer_ms = self._pick_duration(config.WALK_DURATION_RANGE_MS) * 3
            return

        if roll < config.TRAVERSE_PROBABILITY + config.WALK_PROBABILITY:
            self.state = random.choice([MovementState.WALK_LEFT, MovementState.WALK_RIGHT])
            self._state_timer_ms = self._pick_duration(config.WALK_DURATION_RANGE_MS)
            return

        self.state = MovementState.IDLE
        self._state_timer_ms = self._pick_duration(config.IDLE_DURATION_RANGE_MS)

    def _clamp_to_virtual_bounds(self) -> None:
        bounds = self.virtual_bounds()
        self.x = max(bounds.left, min(self.x, bounds.right - self.sprite_size))

    @property
    def bob_offset(self) -> float:
        """A small vertical "breathing" offset applied on top of physics
        while idle/walking, purely cosmetic — never affects ground
        collision, only where the sprite is drawn."""
        if self.state in (MovementState.FALLING, MovementState.DRAGGING):
            return 0.0
        phase = (self._elapsed_ms % config.BOB_PERIOD_MS) / config.BOB_PERIOD_MS
        return math.sin(phase * 2 * math.pi) * config.BOB_AMPLITUDE_PX

    @staticmethod
    def _pick_duration(duration_range_ms: tuple[int, int]) -> float:
        return random.uniform(*duration_range_ms)
