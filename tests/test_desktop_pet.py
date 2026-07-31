from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.desktop_pet import ANIMATIONS, DEFAULT_ATLAS, DesktopPet


class DesktopPetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.pet = DesktopPet(DEFAULT_ATLAS)
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
            "failed", "waiting", "running", "review",
        })
        for state, spec in ANIMATIONS.items():
            self.pet.play_state(state)
            self.assertEqual(self.pet._current_cell(), (spec.row, 0))

    def test_animation_progresses_and_one_shot_returns_idle(self) -> None:
        start = self.pet.frame_index
        QTest.qWait(220)
        self.assertNotEqual(self.pet.frame_index, start)
        self.pet.play_state("waving")
        QTest.qWait(750)
        self.assertEqual(self.pet.state_name, "idle")

    def test_single_and_double_click_actions_and_effects(self) -> None:
        self.pet._handle_single_click()
        self.assertEqual(self.pet.state_name, "waving")
        self.assertGreater(len(self.pet._particles), 0)
        self.pet._handle_double_click()
        self.assertEqual(self.pet.state_name, "jumping")
        self.assertGreaterEqual(len(self.pet._particles), 12)

    def test_real_double_click_does_not_fall_through_to_single_click(self) -> None:
        QTest.mouseDClick(self.pet, Qt.MouseButton.LeftButton, pos=self.pet.rect().center())
        self.assertEqual(self.pet.state_name, "jumping")
        QTest.qWait(QApplication.doubleClickInterval() + 50)
        self.assertEqual(self.pet.state_name, "jumping")

    def test_all_sixteen_look_directions_map_to_v2_rows(self) -> None:
        for index in range(16):
            self.pet.show_look_direction(index * 22.5)
            expected = (9, index) if index < 8 else (10, index - 8)
            self.assertEqual(self.pet._current_cell(), expected)

    def test_pause_auto_top_and_scale_controls(self) -> None:
        self.pet.toggle_pause()
        self.assertTrue(self.pet.paused)
        frame = self.pet.frame_index
        QTest.qWait(220)
        self.assertEqual(self.pet.frame_index, frame)
        self.pet.toggle_pause()
        self.assertFalse(self.pet.paused)
        self.pet.set_auto_actions(True)
        self.assertTrue(self.pet.auto_actions_enabled)
        self.pet.set_always_on_top(False)
        self.assertFalse(self.pet._always_on_top)
        self.pet.set_display_scale(1.25)
        self.assertEqual(self.pet.display_scale, 1.25)
        self.assertEqual(self.pet.size().width(), 240)
        self.assertEqual(self.pet.size().height(), 260)

    def test_context_menu_contains_interactions_and_exit(self) -> None:
        menu = self.pet._build_context_menu()
        labels = [action.text() for action in menu.actions()]
        self.assertIn("互动动作", labels)
        self.assertIn("自动随机动作", labels)
        self.assertIn("始终置顶", labels)
        self.assertIn("显示大小", labels)
        self.assertIn("退出", labels)
        interactions = menu.actions()[0].menu()
        self.assertIsNotNone(interactions)
        interaction_labels = [action.text() for action in interactions.actions()]
        self.assertEqual(interaction_labels[:6], [
            "挥手", "跳一跳", "等待", "认真工作", "检查成果", "有点难过",
        ])


if __name__ == "__main__":
    unittest.main()
