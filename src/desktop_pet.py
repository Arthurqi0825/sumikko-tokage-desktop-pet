from __future__ import annotations

import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import (
    QAbstractAnimation,
    QLockFile,
    QObject,
    QPoint,
    QPointF,
    QRectF,
    QSettings,
    Signal,
    QStandardPaths,
    Qt,
    QTimer,
    QVariantAnimation,
)
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QCursor,
    QIcon,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon, QWidget


CELL_WIDTH = 192
CELL_HEIGHT = 208
APP_NAME = "Tokage Desktop Pet"
APP_VERSION = "1.5.1"
SINGLE_INSTANCE_KEY = "com.local.tokage-desktop-pet.single-instance"
MACOS_NORMAL_WINDOW_LEVEL = 0
MACOS_FLOATING_WINDOW_LEVEL = 3
JUMP_HEIGHT = 96
REACTION_HEIGHT = 22
REST_HOLD_MS = 4200
DEFAULT_ACTION_OPTIONS = (
    ("random", "随机动作"),
    ("idle", "静态站立"),
    ("jumping", "静态跳跃"),
    ("resting", "静态躺下"),
    ("waving", "静态挥手"),
    ("waiting", "静态等待"),
)
DEFAULT_ACTION_NAMES = {name for name, _ in DEFAULT_ACTION_OPTIONS}
DEFAULT_POSE_CELLS = {
    "idle": (0, 0),
    "jumping": (4, 2),
    "resting": (5, 4),
    "waving": (3, 2),
    "waiting": (6, 3),
}


def macos_native_window_level(widget: QWidget) -> int | None:
    """Return the backing NSWindow level for Cocoa runtime validation."""
    app = QApplication.instance()
    if (
        sys.platform != "darwin"
        or app is None
        or app.platformName().lower() != "cocoa"
    ):
        return None
    try:
        import ctypes

        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        send_pointer = ctypes.CFUNCTYPE(
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )(("objc_msgSend", objc))
        send_integer = ctypes.CFUNCTYPE(
            ctypes.c_long,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )(("objc_msgSend", objc))
        native_view = ctypes.c_void_p(int(widget.winId()))
        native_window = send_pointer(native_view, objc.sel_registerName(b"window"))
        if not native_window:
            return None
        return int(send_integer(native_window, objc.sel_registerName(b"level")))
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def set_macos_native_window_level(widget: QWidget, level: int) -> bool:
    """Set the backing NSWindow level without adding a PyObjC dependency."""
    app = QApplication.instance()
    if (
        sys.platform != "darwin"
        or app is None
        or app.platformName().lower() != "cocoa"
    ):
        return False
    try:
        import ctypes

        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        send_pointer = ctypes.CFUNCTYPE(
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )(("objc_msgSend", objc))
        send_void_integer = ctypes.CFUNCTYPE(
            None,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_long,
        )(("objc_msgSend", objc))
        native_view = ctypes.c_void_p(int(widget.winId()))
        native_window = send_pointer(native_view, objc.sel_registerName(b"window"))
        if not native_window:
            return False
        send_void_integer(native_window, objc.sel_registerName(b"setLevel:"), int(level))
        return True
    except (AttributeError, OSError, TypeError, ValueError):
        return False


def set_macos_ignores_mouse_events(widget: QWidget, enabled: bool) -> bool:
    """Allow clicks through transparent sprite pixels on the native NSWindow."""
    app = QApplication.instance()
    if (
        sys.platform != "darwin"
        or app is None
        or app.platformName().lower() != "cocoa"
    ):
        return False
    try:
        import ctypes

        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        send_pointer = ctypes.CFUNCTYPE(
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )(("objc_msgSend", objc))
        send_void_bool = ctypes.CFUNCTYPE(
            None,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_bool,
        )(("objc_msgSend", objc))
        native_view = ctypes.c_void_p(int(widget.winId()))
        native_window = send_pointer(native_view, objc.sel_registerName(b"window"))
        if not native_window:
            return False
        send_void_bool(
            native_window,
            objc.sel_registerName(b"setIgnoresMouseEvents:"),
            bool(enabled),
        )
        return True
    except (AttributeError, OSError, TypeError, ValueError):
        return False


def macos_ignores_mouse_events(widget: QWidget) -> bool | None:
    """Read the native NSWindow click-through state for Cocoa validation."""
    app = QApplication.instance()
    if (
        sys.platform != "darwin"
        or app is None
        or app.platformName().lower() != "cocoa"
    ):
        return None
    try:
        import ctypes

        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
        objc.sel_registerName.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        send_pointer = ctypes.CFUNCTYPE(
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )(("objc_msgSend", objc))
        send_bool = ctypes.CFUNCTYPE(
            ctypes.c_bool,
            ctypes.c_void_p,
            ctypes.c_void_p,
        )(("objc_msgSend", objc))
        native_view = ctypes.c_void_p(int(widget.winId()))
        native_window = send_pointer(native_view, objc.sel_registerName(b"window"))
        if not native_window:
            return None
        return bool(send_bool(native_window, objc.sel_registerName(b"ignoresMouseEvents")))
    except (AttributeError, OSError, TypeError, ValueError):
        return None


class SingleInstanceGuard(QObject):
    """Prevent duplicate pets and wake the already-running instance."""

    activation_requested = Signal()

    def __init__(self, key: str = SINGLE_INSTANCE_KEY) -> None:
        super().__init__()
        self.key = key
        lock_path = Path(QStandardPaths.writableLocation(QStandardPaths.TempLocation)) / f"{key}.lock"
        self.lock = QLockFile(str(lock_path))
        self.lock.setStaleLockTime(0)
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._accept_connections)

    def acquire(self) -> bool:
        if not self.lock.tryLock(0):
            self._notify_existing_instance()
            return False

        # The lock is atomic; removing a stale server path cannot race another
        # process into creating a second pet.
        QLocalServer.removeServer(self.key)
        if self.server.listen(self.key):
            return True
        self.lock.unlock()
        return False

    def _notify_existing_instance(self) -> None:
        probe = QLocalSocket()
        probe.connectToServer(self.key)
        if probe.waitForConnected(250):
            probe.write(b"activate\n")
            probe.waitForBytesWritten(250)
            probe.disconnectFromServer()

    def close(self) -> None:
        was_listening = self.server.isListening()
        self.server.close()
        if was_listening:
            QLocalServer.removeServer(self.key)
        if self.lock.isLocked():
            self.lock.unlock()

    def _accept_connections(self) -> None:
        while self.server.hasPendingConnections():
            connection = self.server.nextPendingConnection()
            if connection is None:
                continue
            connection.readyRead.connect(
                lambda socket=connection: self._handle_message(socket)
            )
            if connection.bytesAvailable():
                self._handle_message(connection)

    def _handle_message(self, connection: QLocalSocket) -> None:
        message = bytes(connection.readAll())
        if b"activate" in message:
            self.activation_requested.emit()
        connection.disconnectFromServer()
        connection.deleteLater()


def resource_root() -> Path:
    """Return the source root or PyInstaller's temporary bundle root."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root)
    return Path(__file__).resolve().parents[1]


DEFAULT_ATLAS = resource_root() / "assets" / "codex" / "tokage" / "spritesheet.webp"


@dataclass(frozen=True)
class AnimationSpec:
    row: int
    frames: int
    interval_ms: int
    loop: bool = True


ANIMATIONS: dict[str, AnimationSpec] = {
    "idle": AnimationSpec(0, 6, 180),
    "running-right": AnimationSpec(1, 8, 105),
    "running-left": AnimationSpec(2, 8, 105),
    "waving": AnimationSpec(3, 4, 150, False),
    "jumping": AnimationSpec(4, 5, 170, False),
    "failed": AnimationSpec(5, 8, 165, False),
    "resting": AnimationSpec(5, 8, 240, False),
    "waiting": AnimationSpec(6, 6, 175, False),
    "running": AnimationSpec(7, 6, 135, False),
    "review": AnimationSpec(8, 6, 155, False),
}


@dataclass
class Particle:
    position: QPointF
    velocity: QPointF
    color: QColor
    radius: float
    life: float = 1.0


@dataclass
class InteractionRing:
    center: QPointF
    radius: float
    color: QColor
    life: float = 1.0


class DesktopPet(QWidget):
    """Transparent, atlas-driven macOS desktop pet."""

    def __init__(
        self,
        atlas_path: Path = DEFAULT_ATLAS,
        *,
        settings: QSettings | None = None,
        persist_settings: bool = True,
    ) -> None:
        super().__init__()
        self._atlas_path = Path(atlas_path)
        self._atlas = QPixmap(str(self._atlas_path))
        if self._atlas.isNull():
            raise RuntimeError(f"Unable to load sprite atlas: {self._atlas_path}")
        if self._atlas.size().width() != CELL_WIDTH * 8 or self._atlas.size().height() != CELL_HEIGHT * 11:
            raise RuntimeError(
                "Sprite atlas must be 1536x2288 "
                f"(received {self._atlas.width()}x{self._atlas.height()})"
            )
        self._atlas_image = self._atlas.toImage()

        self._state_name = "idle"
        self._frame_index = 0
        self._fixed_cell: tuple[int, int] | None = None
        self._paused = False
        self._auto_actions = True
        self._settings = (
            settings
            if settings is not None
            else QSettings("TokageDesktopPet", "TokageDesktopPet")
            if persist_settings
            else None
        )
        saved_default = (
            str(self._settings.value("behavior/defaultAction", "random"))
            if self._settings is not None
            else "random"
        )
        self._default_action = saved_default if saved_default in DEFAULT_ACTION_NAMES else "random"
        self._always_on_top = (
            bool(self._settings.value("window/alwaysOnTop", False, type=bool))
            if self._settings is not None
            else False
        )
        self._mouse_passthrough = False
        self._scale = 1.0
        self._drag_offset: QPoint | None = None
        self._press_global: QPoint | None = None
        self._dragged = False
        self._suppress_click_release = False
        self._last_drag_x = 0
        self._particles: list[Particle] = []
        self._interaction_rings: list[InteractionRing] = []
        self._last_feedback_particle_count = 0
        self._last_feedback_ring_count = 0
        self._click_cycle = 0
        self._jump_base_position: QPoint | None = None
        self._last_jump_height = 0
        self._reaction_base_position: QPoint | None = None
        self._last_reaction_height = 0
        self._rest_phase: str | None = None

        self.setWindowTitle(APP_NAME)
        self.setAccessibleName(APP_NAME)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        if sys.platform == "darwin":
            # A Qt Tool window otherwise disappears when another macOS app is active.
            self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.setMouseTracking(True)
        self._apply_window_flags()
        self.resize(CELL_WIDTH, CELL_HEIGHT)

        self._window_level_timer = QTimer(self)
        self._window_level_timer.setSingleShot(True)
        self._window_level_timer.timeout.connect(self._refresh_native_window_level)

        self._mouse_hit_test_timer = QTimer(self)
        self._mouse_hit_test_timer.setInterval(30)
        self._mouse_hit_test_timer.timeout.connect(self._update_mouse_passthrough)
        self._mouse_hit_test_timer.start()

        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._advance_frame)
        self._frame_timer.start(ANIMATIONS["idle"].interval_ms)

        self._single_click_timer = QTimer(self)
        self._single_click_timer.setSingleShot(True)
        self._single_click_timer.timeout.connect(self._handle_single_click)

        self._look_reset_timer = QTimer(self)
        self._look_reset_timer.setSingleShot(True)
        self._look_reset_timer.timeout.connect(self._return_to_idle)

        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._play_random_action)
        self._schedule_auto_action()

        self._rest_schedule_timer = QTimer(self)
        self._rest_schedule_timer.setSingleShot(True)
        self._rest_schedule_timer.timeout.connect(self._try_auto_rest)

        self._rest_hold_timer = QTimer(self)
        self._rest_hold_timer.setSingleShot(True)
        self._rest_hold_timer.timeout.connect(self._begin_waking)

        self._effect_timer = QTimer(self)
        self._effect_timer.setInterval(33)
        self._effect_timer.timeout.connect(self._update_particles)

        self._jump_animation = QVariantAnimation(self)
        self._jump_animation.setStartValue(0.0)
        self._jump_animation.setEndValue(1.0)
        self._jump_animation.setDuration(
            ANIMATIONS["jumping"].frames * ANIMATIONS["jumping"].interval_ms
        )
        self._jump_animation.valueChanged.connect(self._update_jump_position)
        self._jump_animation.finished.connect(self._finish_jump_motion)

        self._reaction_animation = QVariantAnimation(self)
        self._reaction_animation.setStartValue(0.0)
        self._reaction_animation.setEndValue(1.0)
        self._reaction_animation.setDuration(420)
        self._reaction_animation.valueChanged.connect(self._update_reaction_position)
        self._reaction_animation.finished.connect(self._finish_reaction_motion)

        self.move_to_bottom_right()
        self._apply_default_pose()
        self._schedule_rest()

    @property
    def state_name(self) -> str:
        return self._state_name

    @property
    def frame_index(self) -> int:
        return self._frame_index

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def auto_actions_enabled(self) -> bool:
        return self._auto_actions

    @property
    def display_scale(self) -> float:
        return self._scale

    @property
    def default_action(self) -> str:
        return self._default_action

    @property
    def always_on_top(self) -> bool:
        return self._always_on_top

    @property
    def mouse_passthrough(self) -> bool:
        return self._mouse_passthrough

    @property
    def last_jump_height(self) -> int:
        return self._last_jump_height

    @property
    def last_reaction_height(self) -> int:
        return self._last_reaction_height

    @property
    def rest_phase(self) -> str | None:
        return self._rest_phase

    def status_icon(self) -> QIcon:
        return QIcon(self._atlas.copy(0, 0, CELL_WIDTH, CELL_HEIGHT))

    def _apply_window_flags(self) -> None:
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self._always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def _refresh_native_window_level(self) -> None:
        if not self.isVisible():
            return
        level = (
            MACOS_FLOATING_WINDOW_LEVEL
            if self._always_on_top
            else MACOS_NORMAL_WINDOW_LEVEL
        )
        set_macos_native_window_level(self, level)

    def _sprite_alpha_at(self, position: QPoint) -> int:
        if not self.rect().contains(position):
            return 0
        row, column = self._current_cell()
        source_x = column * CELL_WIDTH + min(
            CELL_WIDTH - 1,
            max(0, int(position.x() * CELL_WIDTH / max(1, self.width()))),
        )
        source_y = row * CELL_HEIGHT + min(
            CELL_HEIGHT - 1,
            max(0, int(position.y() * CELL_HEIGHT / max(1, self.height()))),
        )
        return self._atlas_image.pixelColor(source_x, source_y).alpha()

    def _set_mouse_passthrough(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if enabled == self._mouse_passthrough:
            return
        self._mouse_passthrough = enabled
        set_macos_ignores_mouse_events(self, enabled)

    def _update_mouse_passthrough(self) -> None:
        if not self.isVisible() or self._drag_offset is not None:
            self._set_mouse_passthrough(False)
            return
        local_position = self.mapFromGlobal(QCursor.pos())
        if self.rect().contains(local_position):
            self._set_mouse_passthrough(self._sprite_alpha_at(local_position) < 24)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        # Reapply after Qt recreates the backing NSWindow for flag changes.
        set_macos_ignores_mouse_events(self, self._mouse_passthrough)
        self._window_level_timer.start(0)

    def play_state(self, name: str, *, restart: bool = True) -> None:
        if name not in ANIMATIONS:
            raise ValueError(f"Unknown animation state: {name}")
        if self._paused and name != "idle":
            return
        same_running_state = (
            not restart
            and self._fixed_cell is None
            and self._state_name == name
            and name in ("running-left", "running-right")
        )
        if same_running_state:
            if not self._frame_timer.isActive():
                self._frame_timer.start(ANIMATIONS[name].interval_ms)
            return
        if name == "jumping":
            self._cancel_reaction_motion()
            self._start_jump_motion()
        elif self._jump_animation.state() == QAbstractAnimation.State.Running:
            self._cancel_jump_motion()
        if name == "resting":
            self._rest_phase = "settling"
            self._rest_hold_timer.stop()
        elif self._state_name == "resting":
            self._rest_hold_timer.stop()
            self._rest_phase = None
        self._fixed_cell = None
        self._state_name = name
        if restart:
            self._frame_index = 0
        self._frame_timer.setInterval(ANIMATIONS[name].interval_ms)
        if not self._paused:
            self._frame_timer.start()
        self.update()

    def _start_jump_motion(self) -> None:
        self._cancel_jump_motion()
        self._jump_base_position = self.pos()
        self._last_jump_height = 0
        self._jump_animation.start()

    def _update_jump_position(self, value: object) -> None:
        if self._jump_base_position is None:
            return
        progress = float(value)
        height = round(JUMP_HEIGHT * self._scale * 4.0 * progress * (1.0 - progress))
        self._last_jump_height = max(self._last_jump_height, height)
        self.move(self._jump_base_position.x(), self._jump_base_position.y() - height)

    def _finish_jump_motion(self) -> None:
        if self._jump_base_position is not None:
            self.move(self._jump_base_position)
        self._jump_base_position = None

    def _cancel_jump_motion(self) -> None:
        if self._jump_animation.state() == QAbstractAnimation.State.Running:
            self._jump_animation.stop()
        self._finish_jump_motion()

    def _start_reaction_motion(self) -> None:
        self._cancel_jump_motion()
        self._cancel_reaction_motion()
        self._reaction_base_position = self.pos()
        self._last_reaction_height = 0
        self._reaction_animation.start()

    def _update_reaction_position(self, value: object) -> None:
        if self._reaction_base_position is None:
            return
        progress = float(value)
        height = round(REACTION_HEIGHT * self._scale * math.sin(math.pi * progress))
        self._last_reaction_height = max(self._last_reaction_height, height)
        self.move(self._reaction_base_position.x(), self._reaction_base_position.y() - height)

    def _finish_reaction_motion(self) -> None:
        if self._reaction_base_position is not None:
            self.move(self._reaction_base_position)
        self._reaction_base_position = None

    def _cancel_reaction_motion(self) -> None:
        if self._reaction_animation.state() == QAbstractAnimation.State.Running:
            self._reaction_animation.stop()
        self._finish_reaction_motion()

    def show_look_direction(self, degrees: float) -> None:
        if self._state_name == "resting":
            self._rest_hold_timer.stop()
            self._rest_phase = None
        direction_index = int(round((degrees % 360.0) / 22.5)) % 16
        if direction_index < 8:
            self._fixed_cell = (9, direction_index)
        else:
            self._fixed_cell = (10, direction_index - 8)
        self._state_name = f"look-{direction_index * 22.5:05.1f}"
        self._frame_index = 0
        self._frame_timer.stop()
        self.update()

    def _advance_frame(self) -> None:
        if self._paused or self._fixed_cell is not None:
            return
        if self._state_name == "resting":
            self._advance_rest_frame()
            return
        spec = ANIMATIONS[self._state_name]
        next_frame = self._frame_index + 1
        if next_frame >= spec.frames:
            if spec.loop:
                self._frame_index = 0
            else:
                self._return_to_idle()
                return
        else:
            self._frame_index = next_frame
        self.update()

    def _advance_rest_frame(self) -> None:
        if self._rest_phase == "settling":
            self._frame_index = min(4, self._frame_index + 1)
            if self._frame_index == 4:
                self._rest_phase = "sleeping"
                self._rest_hold_timer.start(REST_HOLD_MS)
        elif self._rest_phase == "sleeping":
            self._frame_index = 3 if self._frame_index == 4 else 4
        elif self._rest_phase == "waking":
            if self._frame_index < 7:
                self._frame_index += 1
            else:
                self._return_to_idle()
                return
        self.update()

    def _begin_waking(self) -> None:
        if self._state_name != "resting":
            return
        self._rest_hold_timer.stop()
        self._rest_phase = "waking"
        self._frame_index = 5
        self._frame_timer.setInterval(180)
        if not self._paused:
            self._frame_timer.start()
        self.update()

    def _try_auto_rest(self) -> None:
        if (
            self._auto_actions
            and self._default_action == "random"
            and not self._paused
            and self._state_name == "idle"
        ):
            self.play_state("resting")
        else:
            self._schedule_rest(short_retry=True)

    def _schedule_rest(self, *, short_retry: bool = False) -> None:
        if (
            not self._auto_actions
            or self._paused
            or self._default_action != "random"
        ):
            self._rest_schedule_timer.stop()
            return
        delay = random.randint(5000, 8000) if short_retry else random.randint(18000, 28000)
        self._rest_schedule_timer.start(delay)

    def _note_user_activity(self) -> None:
        self._schedule_rest()
        if self._state_name == "resting":
            self._begin_waking()

    def _return_to_idle(self) -> None:
        if self._paused or self._drag_offset is not None:
            return
        self._apply_default_pose()

    def _is_default_pose(self) -> bool:
        return self._state_name.startswith("default-")

    def _apply_default_pose(self) -> None:
        if self._default_action == "random":
            self.play_state("idle")
            return
        self._cancel_jump_motion()
        self._cancel_reaction_motion()
        self._rest_hold_timer.stop()
        self._rest_phase = None
        self._fixed_cell = DEFAULT_POSE_CELLS[self._default_action]
        self._state_name = f"default-{self._default_action}"
        self._frame_index = self._fixed_cell[1]
        self._frame_timer.stop()
        self.update()

    def _handle_single_click(self) -> None:
        if self._dragged:
            return
        action = ("waving", "review", "waiting")[self._click_cycle % 3]
        self._click_cycle += 1
        self.play_interaction(action)

    def _handle_double_click(self) -> None:
        self._single_click_timer.stop()
        self._suppress_click_release = True
        self.play_interaction("jumping", intense=True)

    def play_interaction(self, name: str, *, intense: bool = False) -> None:
        self._note_user_activity()
        origin = QPointF(self.width() * 0.52, self.height() * 0.34)
        self._spawn_particles(origin, 28 if intense else 18)
        self._spawn_interaction_rings(origin, 3 if intense else 2)
        if name != "jumping":
            self._start_reaction_motion()
        self.play_state(name)

    def _play_random_action(self) -> None:
        if (
            self._auto_actions
            and self._default_action == "random"
            and not self._paused
            and self._state_name == "idle"
        ):
            action = random.choice(
                ("waving", "jumping", "waiting", "running", "review", "resting", "resting")
            )
            self.play_state(action)
        self._schedule_auto_action()

    def _schedule_auto_action(self) -> None:
        if self._auto_actions and self._default_action == "random":
            self._auto_timer.start(random.randint(7000, 13000))
        else:
            self._auto_timer.stop()

    def _spawn_particles(self, origin: QPointF, count: int) -> None:
        self._last_feedback_particle_count = count
        colors = (
            QColor("#f6a9c5"),
            QColor("#b9e8ed"),
            QColor("#f9d98c"),
            QColor("#d2c1ef"),
        )
        for _ in range(count):
            self._particles.append(
                Particle(
                    QPointF(origin.x() + random.uniform(-15, 15), origin.y() + random.uniform(-8, 8)),
                    QPointF(random.uniform(-1.8, 1.8), random.uniform(-4.0, -1.8)),
                    random.choice(colors),
                    random.uniform(5.0, 10.0),
                )
            )
        if not self._effect_timer.isActive():
            self._effect_timer.start()
        self.update()

    def _spawn_interaction_rings(self, origin: QPointF, count: int) -> None:
        self._last_feedback_ring_count = count
        colors = (QColor("#f6a9c5"), QColor("#8edbe3"), QColor("#f7c95c"))
        for index in range(count):
            self._interaction_rings.append(
                InteractionRing(QPointF(origin), 8.0 + index * 6.0, colors[index % len(colors)])
            )
        if not self._effect_timer.isActive():
            self._effect_timer.start()
        self.update()

    def _update_particles(self) -> None:
        alive: list[Particle] = []
        for particle in self._particles:
            particle.position += particle.velocity
            particle.velocity.setY(particle.velocity.y() + 0.035)
            particle.life -= 0.045
            if particle.life > 0:
                alive.append(particle)
        self._particles = alive
        rings: list[InteractionRing] = []
        for ring in self._interaction_rings:
            ring.radius += 2.8
            ring.life -= 0.06
            if ring.life > 0:
                rings.append(ring)
        self._interaction_rings = rings
        if not alive and not rings:
            self._effect_timer.stop()
        self.update()

    def _current_cell(self) -> tuple[int, int]:
        if self._fixed_cell is not None:
            return self._fixed_cell
        spec = ANIMATIONS[self._state_name]
        return spec.row, min(self._frame_index, spec.frames - 1)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        row, column = self._current_cell()
        source = QRectF(column * CELL_WIDTH, row * CELL_HEIGHT, CELL_WIDTH, CELL_HEIGHT)
        painter.drawPixmap(QRectF(self.rect()), self._atlas, source)
        painter.setPen(Qt.PenStyle.NoPen)
        for particle in self._particles:
            color = QColor(particle.color)
            color.setAlphaF(max(0.0, min(1.0, particle.life)) * 0.85)
            painter.setBrush(color)
            radius = particle.radius * (0.7 + particle.life * 0.3)
            painter.drawEllipse(particle.position, radius, radius)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for ring in self._interaction_rings:
            color = QColor(ring.color)
            color.setAlphaF(max(0.0, min(1.0, ring.life)) * 0.8)
            painter.setPen(QPen(color, max(1.5, 3.5 * ring.life)))
            painter.drawEllipse(ring.center, ring.radius, ring.radius)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._cancel_jump_motion()
            self._cancel_reaction_motion()
            self._note_user_activity()
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._press_global = event.globalPosition().toPoint()
            self._dragged = False
            self._last_drag_x = event.globalPosition().toPoint().x()
            self._look_reset_timer.stop()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        global_position = event.globalPosition().toPoint()
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            if self._press_global is not None and (global_position - self._press_global).manhattanLength() > 5:
                self._dragged = True
            delta_x = global_position.x() - self._last_drag_x
            if abs(delta_x) >= 1:
                drag_state = "running-right" if delta_x > 0 else "running-left"
                if self._state_name != drag_state:
                    self.play_state(drag_state)
            self._last_drag_x = global_position.x()
            self.move(global_position - self._drag_offset)
            event.accept()
            return

        if not self._paused and (self._state_name == "idle" or self._is_default_pose()):
            local = event.position()
            center = QPointF(self.width() / 2.0, self.height() / 2.0)
            vector = local - center
            if abs(vector.x()) + abs(vector.y()) > 18:
                degrees = math.degrees(math.atan2(vector.x(), -vector.y())) % 360.0
                self.show_look_direction(degrees)
                self._look_reset_timer.start(700)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            was_dragged = self._dragged
            self._drag_offset = None
            self._press_global = None
            self.clamp_to_current_screen()
            if was_dragged:
                self._return_to_idle()
            elif self._suppress_click_release:
                self._suppress_click_release = False
            else:
                self._single_click_timer.start(QApplication.doubleClickInterval())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._handle_double_click()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        if self._fixed_cell is not None:
            self._look_reset_timer.start(300)
        super().leaveEvent(event)

    def contextMenuEvent(self, event) -> None:  # type: ignore[override]
        self._build_context_menu().exec(event.globalPos())

    def _build_context_menu(self) -> QMenu:
        menu = QMenu(self)
        actions_menu = QMenu("互动动作", menu)
        menu.addMenu(actions_menu)
        action_specs = (
            ("挥手", "waving"),
            ("跳一跳", "jumping"),
            ("躺下休息", "resting"),
            ("等待", "waiting"),
            ("认真工作", "running"),
            ("检查成果", "review"),
            ("有点难过", "failed"),
        )
        for label, state in action_specs:
            action = actions_menu.addAction(label)
            action.triggered.connect(lambda checked=False, name=state: self.play_interaction(name))
        look_action = actions_menu.addAction("环顾四周")
        look_action.triggered.connect(self._look_around)
        random_action = actions_menu.addAction("随机动作")
        random_action.triggered.connect(self._play_random_action)

        default_menu = QMenu("默认动作", menu)
        menu.addMenu(default_menu)
        default_group = QActionGroup(default_menu)
        default_group.setExclusive(True)
        for name, label in DEFAULT_ACTION_OPTIONS:
            default_action = default_menu.addAction(label)
            default_action.setCheckable(True)
            default_action.setChecked(self._default_action == name)
            default_action.triggered.connect(
                lambda checked=False, value=name: self.set_default_action(value)
            )
            default_group.addAction(default_action)

        menu.addSeparator()
        pause_action = menu.addAction("继续动画" if self._paused else "暂停动画")
        pause_action.triggered.connect(self.toggle_pause)

        auto_action = menu.addAction("启用自动动作")
        auto_action.setCheckable(True)
        auto_action.setChecked(self._auto_actions)
        auto_action.triggered.connect(self.set_auto_actions)

        top_action = menu.addAction("始终置顶")
        top_action.setCheckable(True)
        top_action.setChecked(self._always_on_top)
        top_action.triggered.connect(self.set_always_on_top)

        size_menu = QMenu("显示大小", menu)
        menu.addMenu(size_menu)
        for label, scale in (("75%", 0.75), ("100%", 1.0), ("125%", 1.25), ("150%", 1.5)):
            size_action = size_menu.addAction(label)
            size_action.setCheckable(True)
            size_action.setChecked(math.isclose(self._scale, scale))
            size_action.triggered.connect(lambda checked=False, value=scale: self.set_display_scale(value))

        menu.addAction("回到右下角", self.move_to_bottom_right)
        menu.addSeparator()
        menu.addAction("关于 Tokage Desktop Pet", self.show_about)
        menu.addAction("退出", QApplication.quit)
        # Keep Python wrappers alive for the lifetime of the parent QMenu.
        menu._owned_submenus = [actions_menu, default_menu, size_menu]  # type: ignore[attr-defined]
        menu._default_group = default_group  # type: ignore[attr-defined]
        return menu

    def _look_around(self) -> None:
        directions = iter(range(16))

        def advance() -> None:
            try:
                index = next(directions)
            except StopIteration:
                self._return_to_idle()
                return
            self.show_look_direction(index * 22.5)
            QTimer.singleShot(90, advance)

        advance()

    def toggle_pause(self) -> None:
        self._paused = not self._paused
        if self._paused:
            self._cancel_jump_motion()
            self._cancel_reaction_motion()
            self._single_click_timer.stop()
            self._look_reset_timer.stop()
            self._rest_schedule_timer.stop()
            self._rest_hold_timer.stop()
            self._frame_timer.stop()
        else:
            self._apply_default_pose()
            self._schedule_rest()
        self.update()

    def set_auto_actions(self, enabled: bool) -> None:
        self._auto_actions = bool(enabled)
        self._schedule_auto_action()
        self._schedule_rest()

    def set_default_action(
        self,
        name: str,
        *,
        preview: bool = True,
        persist: bool = True,
    ) -> None:
        if name not in DEFAULT_ACTION_NAMES:
            raise ValueError(f"Unsupported default action: {name}")
        self._default_action = name
        if persist and self._settings is not None:
            self._settings.setValue("behavior/defaultAction", name)
            self._settings.sync()
        self._schedule_auto_action()
        self._schedule_rest()
        if not preview or self._paused:
            return
        self._apply_default_pose()

    def set_always_on_top(self, enabled: bool, *, persist: bool = True) -> None:
        enabled = bool(enabled)
        position = self.pos()
        was_visible = self.isVisible()
        self._always_on_top = enabled
        self._window_level_timer.stop()
        if persist and self._settings is not None:
            self._settings.setValue("window/alwaysOnTop", enabled)
            self._settings.sync()

        # Changing a top-level flag recreates the native NSWindow. Force that
        # recreation now, then restore geometry and visibility deterministically.
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, enabled)
        self.winId()
        self.move(position)
        if was_visible:
            self.show()
            self.move(position)
            if enabled:
                self.raise_()
                set_macos_native_window_level(self, MACOS_FLOATING_WINDOW_LEVEL)
                self._window_level_timer.start(120)
            else:
                # Qt.Tool maps to NSFloatingWindowLevel even after the top hint
                # is removed. Explicitly return it to NSNormalWindowLevel.
                set_macos_native_window_level(self, MACOS_NORMAL_WINDOW_LEVEL)
                self._window_level_timer.start(120)

    def set_display_scale(self, scale: float) -> None:
        if scale not in (0.75, 1.0, 1.25, 1.5):
            raise ValueError(f"Unsupported display scale: {scale}")
        self._cancel_jump_motion()
        self._cancel_reaction_motion()
        center = self.frameGeometry().center()
        self._scale = scale
        self.resize(round(CELL_WIDTH * scale), round(CELL_HEIGHT * scale))
        self.move(center - self.rect().center())
        self.clamp_to_current_screen()
        self.update()

    def move_to_bottom_right(self) -> None:
        self._cancel_jump_motion()
        self._cancel_reaction_motion()
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self.move(area.right() - self.width() - 24, area.bottom() - self.height() - 24)

    def clamp_to_current_screen(self) -> None:
        screen = QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        x = max(area.left(), min(self.x(), area.right() - self.width() + 1))
        y = max(area.top(), min(self.y(), area.bottom() - self.height() + 1))
        self.move(x, y)

    def show_about(self) -> None:
        QMessageBox.information(
            self,
            f"关于 {APP_NAME}",
            f"{APP_NAME} {APP_VERSION}\n\n"
            "单击明显互动 · 双击跳跃 · 可设置静态默认姿态 · 拖动显示跑动动画\n"
            "角色形象版权归 San-X Co., Ltd. 所有，仅供个人非商业实验。",
        )


class MenuBarController:
    """macOS menu-bar controller backed by QSystemTrayIcon."""

    ACTION_SPECS = (
        ("挥手", "waving"),
        ("明显跳跃", "jumping"),
        ("躺下休息", "resting"),
        ("等待", "waiting"),
        ("认真工作", "running"),
        ("检查成果", "review"),
        ("有点难过", "failed"),
    )

    def __init__(self, app: QApplication, pet: DesktopPet, *, show_icon: bool = True) -> None:
        self.app = app
        self.pet = pet
        self.tray = QSystemTrayIcon(pet.status_icon(), pet)
        self.tray.setToolTip(APP_NAME)
        self.menu = QMenu()
        self._build_menu()
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._handle_activation)
        self.menu.aboutToShow.connect(self._sync_state)
        self.app.aboutToQuit.connect(self.tray.hide)
        if show_icon and QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    @property
    def available(self) -> bool:
        return QSystemTrayIcon.isSystemTrayAvailable()

    def _build_menu(self) -> None:
        self.visibility_action = self.menu.addAction("隐藏桌宠")
        self.visibility_action.triggered.connect(self.toggle_pet_visibility)

        interactions = QMenu("互动动作", self.menu)
        self.menu.addMenu(interactions)
        for label, state in self.ACTION_SPECS:
            action = interactions.addAction(label)
            action.triggered.connect(lambda checked=False, name=state: self._show_and_play(name))
        interactions.addAction("环顾四周", self._show_and_look)
        interactions.addAction("随机动作", self._show_and_random)

        defaults = QMenu("默认动作", self.menu)
        self.menu.addMenu(defaults)
        self.default_action_group = QActionGroup(defaults)
        self.default_action_group.setExclusive(True)
        self.default_action_actions: dict[str, QAction] = {}
        for name, label in DEFAULT_ACTION_OPTIONS:
            action = defaults.addAction(label)
            action.setCheckable(True)
            action.triggered.connect(
                lambda checked=False, value=name: self.pet.set_default_action(value)
            )
            self.default_action_group.addAction(action)
            self.default_action_actions[name] = action

        self.menu.addSeparator()
        self.pause_action = self.menu.addAction("暂停动画")
        self.pause_action.triggered.connect(self._toggle_pause)

        self.auto_action = self.menu.addAction("启用自动动作")
        self.auto_action.setCheckable(True)
        self.auto_action.triggered.connect(self.pet.set_auto_actions)

        self.top_action = self.menu.addAction("始终置顶")
        self.top_action.setCheckable(True)
        self.top_action.triggered.connect(self.pet.set_always_on_top)

        sizes = QMenu("显示大小", self.menu)
        self.menu.addMenu(sizes)
        self.size_actions: dict[float, QAction] = {}
        for label, scale in (("75%", 0.75), ("100%", 1.0), ("125%", 1.25), ("150%", 1.5)):
            action = sizes.addAction(label)
            action.setCheckable(True)
            action.triggered.connect(lambda checked=False, value=scale: self.pet.set_display_scale(value))
            self.size_actions[scale] = action

        self.menu.addAction("回到右下角", self._show_and_reset)
        self.menu.addSeparator()
        self.menu.addAction("关于 Tokage Desktop Pet", self.pet.show_about)
        self.menu.addAction("退出", self.app.quit)
        self.menu._owned_submenus = [interactions, defaults, sizes]  # type: ignore[attr-defined]
        self._sync_state()

    def menu_labels(self) -> list[str]:
        return [action.text() for action in self.menu.actions() if not action.isSeparator()]

    def interaction_labels(self) -> list[str]:
        submenu = self.menu._owned_submenus[0]  # type: ignore[attr-defined]
        return [action.text() for action in submenu.actions()]

    def default_action_labels(self) -> list[str]:
        submenu = self.menu._owned_submenus[1]  # type: ignore[attr-defined]
        return [action.text() for action in submenu.actions()]

    def _sync_state(self) -> None:
        self.visibility_action.setText("隐藏桌宠" if self.pet.isVisible() else "显示桌宠")
        self.pause_action.setText("继续动画" if self.pet.paused else "暂停动画")
        self.auto_action.setChecked(self.pet.auto_actions_enabled)
        self.top_action.setChecked(self.pet.always_on_top)
        for name, action in self.default_action_actions.items():
            action.setChecked(self.pet.default_action == name)
        for scale, action in self.size_actions.items():
            action.setChecked(math.isclose(self.pet.display_scale, scale))

    def _ensure_visible(self) -> None:
        if not self.pet.isVisible():
            self.pet.show()
        self.pet.raise_()

    def toggle_pet_visibility(self) -> None:
        if self.pet.isVisible():
            self.pet.hide()
        else:
            self._ensure_visible()
        self._sync_state()

    def _show_and_play(self, state: str) -> None:
        self._ensure_visible()
        self.pet.play_interaction(state, intense=state == "jumping")

    def _show_and_look(self) -> None:
        self._ensure_visible()
        self.pet._look_around()

    def _show_and_random(self) -> None:
        self._ensure_visible()
        self.pet._play_random_action()

    def _toggle_pause(self) -> None:
        self.pet.toggle_pause()
        self._sync_state()

    def _show_and_reset(self) -> None:
        self._ensure_visible()
        self.pet.move_to_bottom_right()

    def _handle_activation(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.toggle_pet_visibility()


def main() -> int:
    if not DEFAULT_ATLAS.exists():
        print(f"Missing desktop-pet sprite atlas: {DEFAULT_ATLAS}", file=sys.stderr)
        return 2
    self_test_output: Path | None = None
    if "--self-test-output" in sys.argv:
        output_index = sys.argv.index("--self-test-output") + 1
        if output_index >= len(sys.argv):
            print("--self-test-output requires a path", file=sys.stderr)
            return 2
        self_test_output = Path(sys.argv[output_index])

    app = QApplication([sys.argv[0]])
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setQuitOnLastWindowClosed(False)
    instance_guard = SingleInstanceGuard()
    if not instance_guard.acquire():
        return 0
    pet = DesktopPet(DEFAULT_ATLAS)
    app.setWindowIcon(pet.status_icon())
    pet.show()
    menu_bar = MenuBarController(app, pet)
    instance_guard.activation_requested.connect(menu_bar._ensure_visible)
    app.aboutToQuit.connect(instance_guard.close)
    app._single_instance_guard = instance_guard  # type: ignore[attr-defined]
    app._menu_bar_controller = menu_bar  # type: ignore[attr-defined]
    if self_test_output is not None:
        _schedule_self_test(app, pet, menu_bar, self_test_output)
    return app.exec()


def _schedule_self_test(
    app: QApplication,
    pet: DesktopPet,
    menu_bar: MenuBarController,
    output_path: Path,
) -> None:
    """Exercise the frozen Cocoa app and persist a machine-readable report."""
    from PySide6.QtCore import QPoint
    from PySide6.QtTest import QTest

    results: dict[str, object] = {
        "app": APP_NAME,
        "version": APP_VERSION,
        "atlas": {
            "path": str(DEFAULT_ATLAS),
            "width": pet._atlas.width(),
            "height": pet._atlas.height(),
        },
        "checks": {},
    }
    checks = results["checks"]
    assert isinstance(checks, dict)
    saved_default_action = pet.default_action
    saved_always_on_top = pet.always_on_top
    pet.set_default_action("random", persist=False)
    initial_frame = pet.frame_index

    def test_single_click() -> None:
        checks["animation_progressed"] = pet.frame_index != initial_frame
        center = pet.rect().center()
        QTest.mouseClick(pet, Qt.MouseButton.LeftButton, pos=center)
        QTimer.singleShot(QApplication.doubleClickInterval() + 300, test_double_click)

    def test_double_click() -> None:
        checks["single_click_state"] = pet.state_name == "waving"
        checks["single_click_particles"] = len(pet._particles) > 0
        checks["single_click_feedback_particles"] = pet._last_feedback_particle_count
        checks["single_click_feedback_rings"] = pet._last_feedback_ring_count
        checks["single_click_reaction_height"] = pet.last_reaction_height
        checks["single_click_effect_is_obvious"] = (
            pet._last_feedback_particle_count >= 18
            and pet._last_feedback_ring_count >= 2
            and pet.last_reaction_height >= 18
        )
        QTest.mouseDClick(pet, Qt.MouseButton.LeftButton, pos=pet.rect().center())
        QTimer.singleShot(430, test_drag)

    def test_drag() -> None:
        checks["double_click_state"] = pet.state_name == "jumping"
        checks["double_click_particles"] = len(pet._particles) >= 28
        checks["double_click_feedback_particles"] = pet._last_feedback_particle_count
        checks["double_click_feedback_rings"] = pet._last_feedback_ring_count
        checks["jump_peak_height"] = pet.last_jump_height
        checks["jump_is_visibly_high"] = pet.last_jump_height >= 80
        pet._cancel_jump_motion()
        pet.play_state("running-right")
        running_start_frame = pet.frame_index
        for _ in range(8):
            pet.play_state("running-right", restart=False)
            QTest.qWait(25)
        checks["drag_animation_progressed"] = pet.frame_index != running_start_frame
        pet.play_state("idle")
        start_position = pet.pos()
        start = pet.rect().center()
        end = start + QPoint(-36, -24)
        QTest.mousePress(pet, Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(pet, end, 60)
        QTest.mouseRelease(pet, Qt.MouseButton.LeftButton, pos=end)
        checks["drag_delta"] = [pet.x() - start_position.x(), pet.y() - start_position.y()]
        checks["drag_state_returned_idle"] = pet.state_name == "idle"
        test_resting()

    def test_resting() -> None:
        pet.play_state("resting")
        pet._frame_timer.stop()
        settling_cells: list[list[int]] = [list(pet._current_cell())]
        for _ in range(4):
            pet._advance_frame()
            settling_cells.append(list(pet._current_cell()))
        checks["rest_settling_cells"] = settling_cells
        checks["rest_lies_down"] = pet.rest_phase == "sleeping" and pet._current_cell() == (5, 4)
        pet._advance_frame()
        checks["rest_breathes_while_sleeping"] = (
            pet.rest_phase == "sleeping" and pet._current_cell() == (5, 3)
        )
        pet._begin_waking()
        pet._frame_timer.stop()
        waking_cells: list[list[int]] = [list(pet._current_cell())]
        for _ in range(3):
            pet._advance_frame()
            waking_cells.append(list(pet._current_cell()))
        checks["rest_waking_cells"] = waking_cells
        checks["rest_returns_idle"] = pet.state_name == "idle"
        test_controls()

    def test_controls() -> None:
        pet.hide()
        duplicate_guard = SingleInstanceGuard()
        checks["duplicate_instance_blocked"] = not duplicate_guard.acquire()
        QTest.qWait(100)
        checks["duplicate_instance_activates_existing"] = pet.isVisible()
        duplicate_guard.close()

        pet.set_default_action("resting", preview=False, persist=False)
        mapped_cells: list[list[int]] = []
        for index in range(16):
            pet.show_look_direction(index * 22.5)
            mapped_cells.append(list(pet._current_cell()))
        checks["look_direction_cells"] = mapped_cells
        checks["look_directions_complete"] = mapped_cells == (
            [[9, index] for index in range(8)] + [[10, index] for index in range(8)]
        )

        menu = pet._build_context_menu()
        labels = [action.text() for action in menu.actions()]
        submenu = menu._owned_submenus[0]  # type: ignore[attr-defined]
        default_submenu = menu._owned_submenus[1]  # type: ignore[attr-defined]
        interaction_labels = [action.text() for action in submenu.actions()]
        default_labels = [action.text() for action in default_submenu.actions()]
        checks["context_menu_labels"] = labels
        checks["interaction_labels"] = interaction_labels
        checks["context_default_action_labels"] = default_labels
        checks["context_menu_complete"] = all(
            label in labels
            for label in ("互动动作", "默认动作", "启用自动动作", "始终置顶", "显示大小", "退出")
        ) and all(
            label in interaction_labels
            for label in ("挥手", "跳一跳", "躺下休息", "等待", "有点难过")
        )
        checks["context_default_action_selected"] = any(
            action.text() == "静态躺下" and action.isChecked()
            for action in default_submenu.actions()
        )
        checks["menu_bar_available"] = menu_bar.available
        checks["menu_bar_visible"] = menu_bar.tray.isVisible()
        checks["menu_bar_labels"] = menu_bar.menu_labels()
        checks["menu_bar_interaction_labels"] = menu_bar.interaction_labels()
        checks["menu_bar_default_action_labels"] = menu_bar.default_action_labels()
        menu_bar._sync_state()
        checks["menu_bar_default_action_selected"] = (
            menu_bar.default_action_actions["resting"].isChecked()
        )
        expected_default_labels = [label for _, label in DEFAULT_ACTION_OPTIONS]
        checks["default_action_menus_complete"] = (
            default_labels == expected_default_labels
            and checks["menu_bar_default_action_labels"] == expected_default_labels
        )
        checks["default_action_sync"] = (
            checks["context_default_action_selected"]
            and checks["menu_bar_default_action_selected"]
        )
        checks["menu_bar_controls_complete"] = all(
            label in checks["menu_bar_labels"]
            for label in (
                "隐藏桌宠",
                "互动动作",
                "默认动作",
                "暂停动画",
                "启用自动动作",
                "始终置顶",
                "显示大小",
                "回到右下角",
                "退出",
            )
        ) and all(
            label in checks["menu_bar_interaction_labels"] for label in ("明显跳跃", "躺下休息")
        )

        static_pose_cells: dict[str, list[int]] = {}
        static_pose_timers_stopped = True
        for name in DEFAULT_POSE_CELLS:
            pet.set_default_action(name, persist=False)
            static_pose_cells[name] = list(pet._current_cell())
            static_pose_timers_stopped = static_pose_timers_stopped and not pet._frame_timer.isActive()
        checks["static_default_pose_cells"] = static_pose_cells
        checks["static_default_poses_complete"] = static_pose_cells == {
            name: list(cell) for name, cell in DEFAULT_POSE_CELLS.items()
        }
        checks["static_default_pose_timers_stopped"] = static_pose_timers_stopped
        pet.set_default_action("jumping", persist=False)
        pet.play_state("waving")
        QTest.qWait(750)
        checks["interaction_returns_to_static_default"] = (
            pet.state_name == "default-jumping"
            and pet._current_cell() == DEFAULT_POSE_CELLS["jumping"]
        )
        pet.set_default_action(saved_default_action, preview=False, persist=False)
        pet._apply_default_pose()
        pet.set_display_scale(1.25)
        checks["scaled_size"] = [pet.width(), pet.height()]
        pet.toggle_pause()
        checks["paused"] = pet.paused
        pet.toggle_pause()
        checks["resumed"] = not pet.paused
        top_position = pet.pos()
        pet.set_always_on_top(False, persist=False)
        app.processEvents()
        native_level_disabled = macos_native_window_level(pet)
        checks["always_on_top_disabled"] = (
            not pet.always_on_top
            and not bool(pet.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        )
        checks["top_toggle_keeps_visible"] = pet.isVisible()
        checks["top_toggle_keeps_position"] = pet.pos() == top_position
        pet.set_always_on_top(True, persist=False)
        app.processEvents()
        native_level_enabled = macos_native_window_level(pet)
        checks["always_on_top_reenabled"] = (
            pet.always_on_top
            and bool(pet.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        )
        checks["native_window_level_disabled"] = native_level_disabled
        checks["native_window_level_enabled"] = native_level_enabled
        checks["native_window_level_toggles"] = (
            sys.platform != "darwin"
            or (
                native_level_disabled is not None
                and native_level_enabled is not None
                and native_level_disabled == MACOS_NORMAL_WINDOW_LEVEL
                and native_level_enabled == MACOS_FLOATING_WINDOW_LEVEL
            )
        )
        pet._set_mouse_passthrough(True)
        native_passthrough_enabled = macos_ignores_mouse_events(pet)
        pet._set_mouse_passthrough(False)
        native_passthrough_disabled = macos_ignores_mouse_events(pet)
        checks["transparent_pixel_alpha"] = pet._sprite_alpha_at(QPoint(0, 0))
        checks["opaque_pixel_alpha"] = pet._sprite_alpha_at(pet.rect().center())
        checks["transparent_mouse_passthrough"] = (
            checks["transparent_pixel_alpha"] < 24
            and checks["opaque_pixel_alpha"] >= 24
            and (
                sys.platform != "darwin"
                or (
                    native_passthrough_enabled is True
                    and native_passthrough_disabled is False
                )
            )
        )
        checks["native_mouse_passthrough_enabled"] = native_passthrough_enabled
        checks["native_mouse_passthrough_disabled"] = native_passthrough_disabled
        checks["native_window_recreated"] = int(pet.winId()) != 0 and pet.windowHandle() is not None
        checks["mac_tool_window_stays_visible_when_inactive"] = (
            sys.platform != "darwin"
            or pet.testAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        )
        menu_bar._sync_state()
        checks["menu_bar_top_state_synced"] = menu_bar.top_action.isChecked()
        checks["transparent_background"] = pet.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        checks["frameless"] = bool(pet.windowFlags() & Qt.WindowType.FramelessWindowHint)
        checks["always_on_top"] = bool(pet.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        checks["tool_window"] = bool(pet.windowFlags() & Qt.WindowType.Tool)
        pet.set_always_on_top(saved_always_on_top, persist=False)
        required_true = (
            "animation_progressed",
            "single_click_state",
            "single_click_particles",
            "single_click_effect_is_obvious",
            "double_click_state",
            "double_click_particles",
            "jump_is_visibly_high",
            "drag_animation_progressed",
            "drag_state_returned_idle",
            "duplicate_instance_blocked",
            "duplicate_instance_activates_existing",
            "rest_lies_down",
            "rest_breathes_while_sleeping",
            "rest_returns_idle",
            "look_directions_complete",
            "context_menu_complete",
            "menu_bar_available",
            "menu_bar_visible",
            "menu_bar_controls_complete",
            "default_action_menus_complete",
            "default_action_sync",
            "static_default_poses_complete",
            "static_default_pose_timers_stopped",
            "interaction_returns_to_static_default",
            "paused",
            "resumed",
            "always_on_top_disabled",
            "top_toggle_keeps_visible",
            "top_toggle_keeps_position",
            "always_on_top_reenabled",
            "native_window_level_toggles",
            "transparent_mouse_passthrough",
            "native_window_recreated",
            "mac_tool_window_stays_visible_when_inactive",
            "menu_bar_top_state_synced",
            "transparent_background",
            "frameless",
            "always_on_top",
            "tool_window",
        )
        checks["all_passed"] = (
            all(checks[key] is True for key in required_true)
            and checks["drag_delta"] == [-36, -24]
            and checks["scaled_size"] == [240, 260]
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        app.quit()

    QTimer.singleShot(260, test_single_click)
