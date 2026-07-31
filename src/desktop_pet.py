from __future__ import annotations

import math
import random
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QCursor, QIcon, QMouseEvent, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QWidget


CELL_WIDTH = 192
CELL_HEIGHT = 208
APP_NAME = "Tokage Desktop Pet"
APP_VERSION = "1.0.0"


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
    "jumping": AnimationSpec(4, 5, 125, False),
    "failed": AnimationSpec(5, 8, 165, False),
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


class DesktopPet(QWidget):
    """Transparent, atlas-driven macOS desktop pet."""

    def __init__(self, atlas_path: Path = DEFAULT_ATLAS) -> None:
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

        self._state_name = "idle"
        self._frame_index = 0
        self._fixed_cell: tuple[int, int] | None = None
        self._paused = False
        self._auto_actions = True
        self._always_on_top = True
        self._scale = 1.0
        self._drag_offset: QPoint | None = None
        self._press_global: QPoint | None = None
        self._dragged = False
        self._suppress_click_release = False
        self._last_drag_x = 0
        self._particles: list[Particle] = []
        self._click_cycle = 0

        self.setWindowTitle(APP_NAME)
        self.setAccessibleName(APP_NAME)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self._apply_window_flags()
        self.resize(CELL_WIDTH, CELL_HEIGHT)

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

        self._effect_timer = QTimer(self)
        self._effect_timer.setInterval(33)
        self._effect_timer.timeout.connect(self._update_particles)

        self.move_to_bottom_right()

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

    def _apply_window_flags(self) -> None:
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self._always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def play_state(self, name: str, *, restart: bool = True) -> None:
        if name not in ANIMATIONS:
            raise ValueError(f"Unknown animation state: {name}")
        if self._paused and name != "idle":
            return
        self._fixed_cell = None
        self._state_name = name
        if restart:
            self._frame_index = 0
        self._frame_timer.setInterval(ANIMATIONS[name].interval_ms)
        if not self._paused:
            self._frame_timer.start()
        self.update()

    def show_look_direction(self, degrees: float) -> None:
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

    def _return_to_idle(self) -> None:
        if self._paused or self._drag_offset is not None:
            return
        self.play_state("idle")

    def _handle_single_click(self) -> None:
        if self._dragged:
            return
        action = ("waving", "review", "waiting")[self._click_cycle % 3]
        self._click_cycle += 1
        self._spawn_particles(QPointF(self.width() * 0.58, self.height() * 0.36), 7)
        self.play_state(action)

    def _handle_double_click(self) -> None:
        self._single_click_timer.stop()
        self._suppress_click_release = True
        self._spawn_particles(QPointF(self.width() * 0.5, self.height() * 0.28), 12)
        self.play_state("jumping")

    def _play_random_action(self) -> None:
        if self._auto_actions and not self._paused and self._state_name == "idle":
            self.play_state(random.choice(("waving", "jumping", "waiting", "running", "review")))
        self._schedule_auto_action()

    def _schedule_auto_action(self) -> None:
        if self._auto_actions:
            self._auto_timer.start(random.randint(7000, 13000))
        else:
            self._auto_timer.stop()

    def _spawn_particles(self, origin: QPointF, count: int) -> None:
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
                    QPointF(random.uniform(-0.8, 0.8), random.uniform(-2.4, -1.0)),
                    random.choice(colors),
                    random.uniform(3.0, 7.0),
                )
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
        if not alive:
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

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
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
                self.play_state("running-right" if delta_x > 0 else "running-left", restart=False)
            self._last_drag_x = global_position.x()
            self.move(global_position - self._drag_offset)
            event.accept()
            return

        if not self._paused and self._state_name == "idle":
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
                self.play_state("idle")
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
            ("等待", "waiting"),
            ("认真工作", "running"),
            ("检查成果", "review"),
            ("有点难过", "failed"),
        )
        for label, state in action_specs:
            action = actions_menu.addAction(label)
            action.triggered.connect(lambda checked=False, name=state: self.play_state(name))
        look_action = actions_menu.addAction("环顾四周")
        look_action.triggered.connect(self._look_around)
        random_action = actions_menu.addAction("随机动作")
        random_action.triggered.connect(self._play_random_action)

        menu.addSeparator()
        pause_action = menu.addAction("继续动画" if self._paused else "暂停动画")
        pause_action.triggered.connect(self.toggle_pause)

        auto_action = menu.addAction("自动随机动作")
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
        menu._owned_submenus = [actions_menu, size_menu]  # type: ignore[attr-defined]
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
            self._single_click_timer.stop()
            self._look_reset_timer.stop()
            self._frame_timer.stop()
        else:
            self.play_state("idle")
        self.update()

    def set_auto_actions(self, enabled: bool) -> None:
        self._auto_actions = bool(enabled)
        self._schedule_auto_action()

    def set_always_on_top(self, enabled: bool) -> None:
        position = self.pos()
        was_visible = self.isVisible()
        self._always_on_top = bool(enabled)
        self._apply_window_flags()
        self.move(position)
        if was_visible:
            self.show()

    def set_display_scale(self, scale: float) -> None:
        if scale not in (0.75, 1.0, 1.25, 1.5):
            raise ValueError(f"Unsupported display scale: {scale}")
        center = self.frameGeometry().center()
        self._scale = scale
        self.resize(round(CELL_WIDTH * scale), round(CELL_HEIGHT * scale))
        self.move(center - self.rect().center())
        self.clamp_to_current_screen()
        self.update()

    def move_to_bottom_right(self) -> None:
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
            "单击互动 · 双击跳跃 · 拖动移动 · 右键打开动作菜单\n"
            "角色形象版权归 San-X Co., Ltd. 所有，仅供个人非商业实验。",
        )


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
    app.setQuitOnLastWindowClosed(True)
    app.setWindowIcon(QIcon(str(DEFAULT_ATLAS)))
    pet = DesktopPet(DEFAULT_ATLAS)
    pet.show()
    if self_test_output is not None:
        _schedule_self_test(app, pet, self_test_output)
    return app.exec()


def _schedule_self_test(app: QApplication, pet: DesktopPet, output_path: Path) -> None:
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
    initial_frame = pet.frame_index

    def test_single_click() -> None:
        checks["animation_progressed"] = pet.frame_index != initial_frame
        center = pet.rect().center()
        QTest.mouseClick(pet, Qt.MouseButton.LeftButton, pos=center)
        QTimer.singleShot(QApplication.doubleClickInterval() + 80, test_double_click)

    def test_double_click() -> None:
        checks["single_click_state"] = pet.state_name == "waving"
        checks["single_click_particles"] = len(pet._particles) > 0
        QTest.mouseDClick(pet, Qt.MouseButton.LeftButton, pos=pet.rect().center())
        QTimer.singleShot(80, test_drag)

    def test_drag() -> None:
        checks["double_click_state"] = pet.state_name == "jumping"
        checks["double_click_particles"] = len(pet._particles) >= 12
        start_position = pet.pos()
        start = pet.rect().center()
        end = start + QPoint(-36, -24)
        QTest.mousePress(pet, Qt.MouseButton.LeftButton, pos=start)
        QTest.mouseMove(pet, end, 60)
        QTest.mouseRelease(pet, Qt.MouseButton.LeftButton, pos=end)
        checks["drag_delta"] = [pet.x() - start_position.x(), pet.y() - start_position.y()]
        checks["drag_state_returned_idle"] = pet.state_name == "idle"
        test_controls()

    def test_controls() -> None:
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
        interaction_labels = [action.text() for action in submenu.actions()]
        checks["context_menu_labels"] = labels
        checks["interaction_labels"] = interaction_labels
        checks["context_menu_complete"] = all(
            label in labels for label in ("互动动作", "自动随机动作", "始终置顶", "显示大小", "退出")
        ) and interaction_labels[:6] == [
            "挥手", "跳一跳", "等待", "认真工作", "检查成果", "有点难过",
        ]

        pet.set_display_scale(1.25)
        checks["scaled_size"] = [pet.width(), pet.height()]
        pet.toggle_pause()
        checks["paused"] = pet.paused
        pet.toggle_pause()
        checks["resumed"] = not pet.paused
        checks["transparent_background"] = pet.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        checks["frameless"] = bool(pet.windowFlags() & Qt.WindowType.FramelessWindowHint)
        checks["always_on_top"] = bool(pet.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        checks["tool_window"] = bool(pet.windowFlags() & Qt.WindowType.Tool)
        checks["all_passed"] = all(
            value is True
            for key, value in checks.items()
            if key not in {"drag_delta", "look_direction_cells", "context_menu_labels", "interaction_labels", "scaled_size"}
        ) and checks["drag_delta"] == [-36, -24] and checks["scaled_size"] == [240, 260]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        app.quit()

    QTimer.singleShot(260, test_single_click)
