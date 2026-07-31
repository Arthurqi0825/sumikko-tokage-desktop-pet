from __future__ import annotations

import os
import tempfile
import unittest
import uuid
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.desktop_pet import (
    ANIMATIONS,
    DEFAULT_ACTION_OPTIONS,
    DEFAULT_POSE_CELLS,
    DEFAULT_ATLAS,
    DesktopPet,
    MenuBarController,
    SingleInstanceGuard,
)


class DesktopPetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.pet = DesktopPet(DEFAULT_ATLAS, persist_settings=False)
        self.pet.set_auto_actions(False)
        self.pet.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        self.pet.close()
        self.app.processEvents()

    def test_atlas_and_all_standard_states(self) -> None:
        self.assertEqual(self.pet._atlas.size().width(), 1536)
        self.assertEqual(self.pet._atlas.size().height(), 2288)
        self.assertEqual(set(ANIMATIONS), {
            "idle", "running-right", "running-left", "waving", "jumping",
            "failed", "resting", "waiting", "running", "review",
        })
        for state, spec in ANIMATIONS.items():
            self.pet.play_state(state)
            self.assertEqual(self.pet._current_cell(), (spec.row, 0))

    def test_animation_progresses_and_one_shot_returns_idle(self) -> None:
        start = self.pet.frame_index
        QTest.qWait(300)
        self.assertNotEqual(self.pet.frame_index, start)
        self.pet.play_state("waving")
        QTest.qWait(950)
        self.assertEqual(self.pet.state_name, "idle")

    def test_repeated_drag_events_do_not_freeze_running_animation(self) -> None:
        self.pet.play_state("running-right")
        start = self.pet.frame_index
        for _ in range(8):
            self.pet.play_state("running-right", restart=False)
            QTest.qWait(25)
        self.assertNotEqual(self.pet.frame_index, start)
        self.pet.play_state("running-left")
        QTest.qWait(180)
        self.assertGreater(self.pet.frame_index, 0)

    def test_single_and_double_click_actions_and_effects(self) -> None:
        self.pet._handle_single_click()
        self.assertEqual(self.pet.state_name, "waving")
        self.assertGreaterEqual(len(self.pet._particles), 18)
        self.assertGreaterEqual(len(self.pet._interaction_rings), 2)
        self.pet._handle_double_click()
        self.assertEqual(self.pet.state_name, "jumping")
        self.assertGreaterEqual(len(self.pet._particles), 28)
        self.assertGreaterEqual(len(self.pet._interaction_rings), 3)

    def test_single_click_has_visible_reaction_bounce(self) -> None:
        origin = self.pet.pos()
        self.pet._handle_single_click()
        QTest.qWait(280)
        self.assertGreaterEqual(self.pet.last_reaction_height, 18)
        self.assertLessEqual(self.pet.y(), origin.y() - 18)
        QTest.qWait(340)
        self.assertEqual(self.pet.pos(), origin)

    def test_real_double_click_does_not_fall_through_to_single_click(self) -> None:
        QTest.mouseDClick(self.pet, Qt.MouseButton.LeftButton, pos=self.pet.rect().center())
        self.assertEqual(self.pet.state_name, "jumping")
        QTest.qWait(QApplication.doubleClickInterval() + 50)
        self.assertEqual(self.pet.state_name, "jumping")

    def test_jump_has_visible_vertical_lift_and_lands_at_origin(self) -> None:
        origin = self.pet.pos()
        self.pet.play_state("jumping")
        QTest.qWait(550)
        self.assertGreaterEqual(self.pet.last_jump_height, 80)
        self.assertLessEqual(self.pet.y(), origin.y() - 80)
        QTest.qWait(600)
        self.assertEqual(self.pet.pos(), origin)
        self.assertEqual(self.pet.state_name, "idle")

    def test_resting_lies_down_holds_and_wakes(self) -> None:
        self.pet.play_state("resting")
        self.pet._frame_timer.stop()
        for _ in range(4):
            self.pet._advance_frame()
        self.assertEqual(self.pet.rest_phase, "sleeping")
        self.assertEqual(self.pet._current_cell(), (5, 4))
        self.pet._advance_frame()
        self.assertEqual(self.pet._current_cell(), (5, 3))
        self.pet._begin_waking()
        self.pet._frame_timer.stop()
        self.assertEqual(self.pet.rest_phase, "waking")
        self.assertEqual(self.pet._current_cell(), (5, 5))
        for _ in range(3):
            self.pet._advance_frame()
        self.assertEqual(self.pet.state_name, "idle")

    def test_all_sixteen_look_directions_map_to_v2_rows(self) -> None:
        for index in range(16):
            self.pet.show_look_direction(index * 22.5)
            expected = (9, index) if index < 8 else (10, index - 8)
            self.assertEqual(self.pet._current_cell(), expected)

    def test_pause_auto_and_scale_controls(self) -> None:
        self.pet.toggle_pause()
        self.assertTrue(self.pet.paused)
        frame = self.pet.frame_index
        QTest.qWait(220)
        self.assertEqual(self.pet.frame_index, frame)
        self.pet.toggle_pause()
        self.assertFalse(self.pet.paused)
        self.pet.set_auto_actions(True)
        self.assertTrue(self.pet.auto_actions_enabled)
        self.pet.set_display_scale(1.25)
        self.assertEqual(self.pet.display_scale, 1.25)
        self.assertEqual(self.pet.size().width(), 240)
        self.assertEqual(self.pet.size().height(), 260)
        self.pet.set_display_scale(0.10)
        self.assertEqual(self.pet.display_scale, 0.10)
        self.assertEqual(self.pet.size().width(), 19)
        self.assertEqual(self.pet.size().height(), 21)

    def test_animation_speed_and_display_scale_persist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings_path = Path(directory) / "settings.ini"
            first = DesktopPet(
                DEFAULT_ATLAS,
                settings=QSettings(str(settings_path), QSettings.Format.IniFormat),
            )
            first.set_animation_speed(0.65)
            first.set_display_scale(0.37)
            self.assertEqual(
                first._animation_interval("idle"),
                round(ANIMATIONS["idle"].interval_ms / 0.65),
            )
            first.close()

            second = DesktopPet(
                DEFAULT_ATLAS,
                settings=QSettings(str(settings_path), QSettings.Format.IniFormat),
            )
            self.assertEqual(second.animation_speed, 0.65)
            self.assertEqual(second.display_scale, 0.37)
            self.assertEqual(second.width(), round(192 * 0.37))
            self.assertEqual(second.height(), round(208 * 0.37))
            second.close()

    def test_always_on_top_toggle_keeps_native_window_visible_and_positioned(self) -> None:
        position = self.pet.pos()
        native_id = int(self.pet.winId())
        self.pet.set_always_on_top(False, persist=False)
        self.app.processEvents()
        self.assertFalse(self.pet.always_on_top)
        self.assertFalse(self.pet.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        self.assertTrue(self.pet.isVisible())
        self.assertEqual(self.pet.pos(), position)
        self.assertNotEqual(int(self.pet.winId()), 0)

        self.pet.set_always_on_top(True, persist=False)
        self.app.processEvents()
        self.assertTrue(self.pet.always_on_top)
        self.assertTrue(self.pet.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        self.assertTrue(self.pet.isVisible())
        self.assertEqual(self.pet.pos(), position)
        self.assertNotEqual(native_id, 0)
        self.pet._window_level_timer.stop()
        self.pet._handle_application_state_change(Qt.ApplicationState.ApplicationInactive)
        self.assertTrue(self.pet._window_level_timer.isActive())

    def test_transparent_sprite_pixels_are_mouse_passthrough(self) -> None:
        self.pet.play_state("idle")
        self.assertEqual(self.pet._sprite_alpha_at(QPoint(0, 0)), 0)
        self.assertGreaterEqual(
            self.pet._sprite_alpha_at(self.pet.rect().center()),
            24,
        )
        self.pet._set_mouse_passthrough(True)
        self.assertTrue(self.pet.mouse_passthrough)
        self.pet._set_mouse_passthrough(False)
        self.assertFalse(self.pet.mouse_passthrough)

    def test_always_on_top_setting_persists_and_menu_bar_syncs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            settings_path = Path(directory) / "settings.ini"
            settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
            first = DesktopPet(DEFAULT_ATLAS, settings=settings)
            first.set_always_on_top(False)
            first.close()

            second = DesktopPet(
                DEFAULT_ATLAS,
                settings=QSettings(str(settings_path), QSettings.Format.IniFormat),
            )
            self.assertFalse(second.always_on_top)
            controller = MenuBarController(self.app, second, show_icon=False)
            controller._sync_state()
            self.assertFalse(controller.top_action.isChecked())
            second.set_always_on_top(True)
            controller._sync_state()
            self.assertTrue(controller.top_action.isChecked())
            second.close()

    def test_single_instance_guard_blocks_duplicate_and_activates_first(self) -> None:
        key = f"tokage-test-{uuid.uuid4()}"
        first = SingleInstanceGuard(key)
        activated: list[bool] = []
        first.activation_requested.connect(lambda: activated.append(True))
        if not first.acquire():
            self.skipTest("The current sandbox does not permit local IPC sockets")

        second = SingleInstanceGuard(key)
        self.assertFalse(second.acquire())
        QTest.qWait(80)
        self.assertEqual(activated, [True])
        first.close()

    def test_default_action_controls_scheduler_and_persists(self) -> None:
        self.pet.set_default_action("jumping", persist=False)
        self.pet.set_auto_actions(True)
        self.assertEqual(self.pet.state_name, "default-jumping")
        self.assertEqual(self.pet._current_cell(), DEFAULT_POSE_CELLS["jumping"])
        self.assertFalse(self.pet._frame_timer.isActive())
        self.pet._play_random_action()
        self.assertEqual(self.pet.state_name, "default-jumping")

        self.pet.play_state("waving")
        QTest.qWait(950)
        self.assertEqual(self.pet.state_name, "default-jumping")
        self.assertEqual(self.pet._current_cell(), DEFAULT_POSE_CELLS["jumping"])

        with tempfile.TemporaryDirectory() as directory:
            settings = QSettings(str(Path(directory) / "settings.ini"), QSettings.Format.IniFormat)
            first = DesktopPet(DEFAULT_ATLAS, settings=settings)
            first.set_auto_actions(False)
            first.set_default_action("resting", preview=False)
            first.close()
            second = DesktopPet(DEFAULT_ATLAS, settings=settings)
            second.set_auto_actions(False)
            self.assertEqual(second.default_action, "resting")
            second.close()

    def test_context_menu_contains_interactions_and_exit(self) -> None:
        menu = self.pet._build_context_menu()
        labels = [action.text() for action in menu.actions()]
        self.assertIn("互动动作", labels)
        self.assertIn("默认动作", labels)
        self.assertIn("启用自动动作", labels)
        self.assertIn("始终置顶", labels)
        self.assertIn("动画速度", labels)
        self.assertIn("显示大小", labels)
        self.assertIn("退出", labels)
        interactions = menu.actions()[0].menu()
        self.assertIsNotNone(interactions)
        interaction_labels = [action.text() for action in interactions.actions()]
        self.assertEqual(interaction_labels[:6], [
            "挥手", "跳一跳", "躺下休息", "等待", "认真工作", "检查成果",
        ])
        self.assertIn("有点难过", interaction_labels)
        defaults = next(action.menu() for action in menu.actions() if action.text() == "默认动作")
        self.assertIsNotNone(defaults)
        self.assertEqual(
            [action.text() for action in defaults.actions()],
            [label for _, label in DEFAULT_ACTION_OPTIONS],
        )
        self.assertEqual(menu._speed_slider.minimum(), 50)  # type: ignore[attr-defined]
        self.assertEqual(menu._speed_slider.maximum(), 200)  # type: ignore[attr-defined]
        self.assertEqual(menu._size_slider.minimum(), 10)  # type: ignore[attr-defined]
        self.assertEqual(menu._size_slider.maximum(), 200)  # type: ignore[attr-defined]
        menu._speed_slider.setValue(75)  # type: ignore[attr-defined]
        menu._size_slider.setValue(35)  # type: ignore[attr-defined]
        self.assertEqual(self.pet.animation_speed, 0.75)
        self.assertEqual(self.pet.display_scale, 0.35)

    def test_macos_menu_bar_controller_contains_all_controls(self) -> None:
        controller = MenuBarController(self.app, self.pet, show_icon=False)
        labels = controller.menu_labels()
        self.assertIn("隐藏桌宠", labels)
        self.assertIn("互动动作", labels)
        self.assertIn("默认动作", labels)
        self.assertIn("暂停动画", labels)
        self.assertIn("启用自动动作", labels)
        self.assertIn("始终置顶", labels)
        self.assertIn("动画速度", labels)
        self.assertIn("显示大小", labels)
        self.assertIn("回到右下角", labels)
        self.assertIn("退出", labels)
        self.assertIn("明显跳跃", controller.interaction_labels())
        self.assertIn("躺下休息", controller.interaction_labels())
        self.assertIn("静态跳跃", controller.default_action_labels())
        self.assertIn("静态躺下", controller.default_action_labels())
        self.pet.set_default_action("resting", preview=False, persist=False)
        controller._sync_state()
        self.assertTrue(controller.default_action_actions["resting"].isChecked())
        self.assertEqual(controller.speed_slider.minimum(), 50)
        self.assertEqual(controller.speed_slider.maximum(), 200)
        self.assertEqual(controller.size_slider.minimum(), 10)
        self.assertEqual(controller.size_slider.maximum(), 200)
        self.pet.set_animation_speed(0.8, persist=False)
        self.pet.set_display_scale(0.4, persist=False)
        controller._sync_state()
        self.assertEqual(controller.speed_slider.value(), 80)
        self.assertEqual(controller.size_slider.value(), 40)
        controller.toggle_pet_visibility()
        self.assertFalse(self.pet.isVisible())
        controller.toggle_pet_visibility()
        self.assertTrue(self.pet.isVisible())


if __name__ == "__main__":
    unittest.main()
