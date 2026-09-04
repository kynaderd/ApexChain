"""
ui.py
-----
The Qt side of Azuki: a small frameless, transparent, always-on-top
window that draws the creature itself (no external image assets — it's
all vector shapes via QPainter), reads its position each tick from
movement.Movement, and forwards mouse interactions (click, drag,
double-click-to-chat) into reactions from brain.AzukiBrain.

Also owns the system tray icon, since a borderless always-on-top widget
needs *some* obvious way to quit or configure it.
"""

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QInputDialog, QMenu, QSystemTrayIcon, QWidget

from . import config
from .brain import AzukiBrain
from .movement import Movement, MovementState


class AzukiWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.brain = AzukiBrain()
        self.movement = Movement(x=200.0, y=200.0, sprite_size=config.SPRITE_SIZE)
        self._refresh_screens()

        self._speech_text: str | None = None
        self._speech_timer = QTimer(self)
        self._speech_timer.setSingleShot(True)
        self._speech_timer.timeout.connect(self._clear_speech)

        self._drag_offset = QPoint()
        self._last_mouse_global = QPoint()
        self._drag_velocity = (0.0, 0.0)
        self._click_through = False

        self._configure_window()
        self._build_tray_icon()

        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._on_tick)
        self._tick_timer.start(config.TICK_MS)

        # Say hello shortly after startup.
        QTimer.singleShot(600, lambda: self._say(self.brain.idle_mutter()))

    # -- window setup ---------------------------------------------------------

    def _configure_window(self) -> None:
        bubble_headroom = 90  # extra space above the sprite for the speech bubble
        self.setFixedSize(config.SPRITE_SIZE, config.SPRITE_SIZE + bubble_headroom)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool  # keeps Azuki off the taskbar/alt-tab list
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self._reposition_window()

    def _refresh_screens(self) -> None:
        rects = [s.geometry().getRect() for s in QGuiApplication.screens()]
        self.movement.set_screens(rects)

    def _reposition_window(self) -> None:
        # The Movement's (x, y) is the sprite's top-left; the window is
        # taller (for the speech bubble above it), so offset accordingly.
        bubble_headroom = self.height() - config.SPRITE_SIZE
        self.move(int(self.movement.x), int(self.movement.y) - bubble_headroom)

    # -- tray icon ---------------------------------------------------------

    def _build_tray_icon(self) -> None:
        self._tray = QSystemTrayIcon(self._render_icon(), self)
        self._tray.setToolTip(config.TRAY_TOOLTIP)

        menu = QMenu()

        chat_action = QAction("Talk to Azuki...", self)
        chat_action.triggered.connect(self._open_chat_dialog)
        menu.addAction(chat_action)

        self._click_through_action = QAction("Click-through mode", self)
        self._click_through_action.setCheckable(True)
        self._click_through_action.toggled.connect(self._set_click_through)
        menu.addAction(self._click_through_action)

        reset_action = QAction("Reset conversation", self)
        reset_action.triggered.connect(self.brain.reset)
        menu.addAction(reset_action)

        menu.addSeparator()
        quit_action = QAction("Quit Azuki", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)
        self._tray.show()

    def _render_icon(self) -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        self._paint_bean(painter, QRect(4, 4, 56, 56), bob=0.0)
        painter.end()
        return QIcon(pixmap)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self.setVisible(not self.isVisible())

    def _set_click_through(self, enabled: bool) -> None:
        self._click_through = enabled
        self.setWindowFlag(Qt.WindowTransparentForInput, enabled)
        self.show()  # flag changes require re-showing the window to take effect

    def _quit(self) -> None:
        QGuiApplication.instance().quit()

    # -- main loop ---------------------------------------------------------

    def _on_tick(self) -> None:
        self.movement.update(config.TICK_MS)
        self._reposition_window()
        self.update()  # trigger a repaint

    # -- speech bubble ---------------------------------------------------------

    def _say(self, text: str) -> None:
        self._speech_text = text
        self.movement.start_talking()
        self._speech_timer.start(config.BUBBLE_DURATION_MS)
        self.update()

    def _clear_speech(self) -> None:
        self._speech_text = None
        self.movement.stop_talking()
        self.update()

    def _open_chat_dialog(self) -> None:
        text, ok = QInputDialog.getText(self, "Talk to Azuki", "Say something:")
        if ok and text.strip():
            reply = self.brain.reply(text.strip())
            self._say(reply)

    # -- mouse interactions ---------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.position().toPoint()
            self._last_mouse_global = event.globalPosition().toPoint()
            self.movement.begin_drag()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.LeftButton:
            global_pos = event.globalPosition().toPoint()
            delta = global_pos - self._last_mouse_global
            self._drag_velocity = (delta.x() / (config.TICK_MS / 1000.0), delta.y() / (config.TICK_MS / 1000.0))
            self._last_mouse_global = global_pos

            bubble_headroom = self.height() - config.SPRITE_SIZE
            new_window_pos = self.mapToGlobal(event.position().toPoint() - self._drag_offset)
            self.movement.drag_to(new_window_pos.x(), new_window_pos.y() + bubble_headroom)
            self._reposition_window()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            if self.movement.state == MovementState.DRAGGING:
                vx, vy = self._drag_velocity
                self.movement.end_drag(vx, vy)
                self._say(self.brain.drag_reaction())

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._open_chat_dialog()

    def enterEvent(self, event) -> None:  # cursor hovers over Azuki
        if self._speech_text is None and self.movement.state not in (
            MovementState.DRAGGING,
            MovementState.TALKING,
        ):
            self._say(self.brain.poke_reaction())

    # -- painting ---------------------------------------------------------

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        bubble_headroom = self.height() - config.SPRITE_SIZE
        bean_rect = QRect(0, int(bubble_headroom + self.movement.bob_offset), config.SPRITE_SIZE, config.SPRITE_SIZE)

        if self._speech_text:
            self._paint_speech_bubble(painter, self._speech_text, bean_rect)

        self._paint_bean(painter, bean_rect, self.movement.bob_offset, facing=self._facing())
        painter.end()

    def _facing(self) -> int:
        """-1 for facing left, 1 for facing right — used to mirror the eyes
        so Azuki visibly looks the way it's walking."""
        if self.movement.state == MovementState.WALK_LEFT:
            return -1
        if self.movement.state in (MovementState.WALK_RIGHT, MovementState.TRAVERSING):
            return 1
        return 1

    def _paint_bean(self, painter: QPainter, rect: QRect, bob: float, facing: int = 1) -> None:
        # Body: a slightly squashed rounded shape reminiscent of an azuki bean.
        body_path = QPainterPath()
        body_path.addRoundedRect(
            float(rect.x()), float(rect.y()), float(rect.width()), float(rect.height()), 26.0, 22.0
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(config.BODY_COLOR)))
        painter.drawPath(body_path)

        # A soft highlight near the top-left for a little dimensionality.
        highlight = QPainterPath()
        highlight.addEllipse(rect.x() + rect.width() * 0.18, rect.y() + rect.height() * 0.15, rect.width() * 0.35, rect.height() * 0.25)
        painter.setBrush(QBrush(QColor(config.BODY_HIGHLIGHT)))
        painter.drawPath(highlight)

        # The pale seam line real azuki beans have, running across the middle.
        seam_pen = QPen(QColor(config.SEAM_COLOR))
        seam_pen.setWidthF(3.0)
        painter.setPen(seam_pen)
        seam_y = rect.y() + rect.height() * 0.58
        painter.drawLine(int(rect.x() + rect.width() * 0.12), int(seam_y), int(rect.x() + rect.width() * 0.88), int(seam_y))

        # Eyes, mirrored based on facing direction.
        eye_y = rect.y() + rect.height() * 0.38
        eye_dx = rect.width() * 0.18 * facing
        eye_r = rect.width() * 0.07
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(config.EYE_COLOR)))
        cx = rect.x() + rect.width() / 2
        painter.drawEllipse(int(cx - eye_dx - eye_r), int(eye_y - eye_r), int(eye_r * 2), int(eye_r * 2))
        painter.drawEllipse(int(cx + eye_dx - eye_r), int(eye_y - eye_r), int(eye_r * 2), int(eye_r * 2))

    def _paint_speech_bubble(self, painter: QPainter, text: str, bean_rect: QRect) -> None:
        font = QFont()
        font.setPointSize(9)
        painter.setFont(font)
        metrics = QFontMetrics(font)

        wrapped = self._wrap_text(text, config.BUBBLE_MAX_CHARS_PER_LINE)
        line_height = metrics.height()
        text_width = max(metrics.horizontalAdvance(line) for line in wrapped)
        padding = 10

        bubble_w = text_width + padding * 2
        bubble_h = line_height * len(wrapped) + padding * 2
        bubble_x = max(0, min(bean_rect.center().x() - bubble_w // 2, self.width() - bubble_w))
        bubble_y = max(0, bean_rect.y() - bubble_h - 8)

        bubble_rect = QRect(int(bubble_x), int(bubble_y), int(bubble_w), int(bubble_h))

        painter.setPen(QPen(QColor(config.BUBBLE_BORDER), 1.5))
        painter.setBrush(QBrush(QColor(config.BUBBLE_BG)))
        painter.drawRoundedRect(bubble_rect, 10, 10)

        painter.setPen(QColor(config.BUBBLE_TEXT))
        for i, line in enumerate(wrapped):
            painter.drawText(
                bubble_rect.x() + padding,
                bubble_rect.y() + padding + line_height * (i + 1) - metrics.descent(),
                line,
            )

    @staticmethod
    def _wrap_text(text: str, max_chars: int) -> list[str]:
        words = text.split()
        lines: list[str] = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) > max_chars and current:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines or [text]
