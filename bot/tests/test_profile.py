import unittest

from handlers.profile import (
    _achievements_keyboard,
    _profile_keyboard,
    _render_all_achievements,
    _render_achievements,
    _render_levels,
    _render_profile,
    _render_stats,
    _stats_keyboard,
    _submenu_keyboard,
)
from keyboards.member import member_main_keyboard
from models.events import BotNotificationEvent


def sample_stats() -> dict:
    return {
        "level": 2,
        "levelName": "Исполнитель",
        "xp": 450,
        "xpForCurrentLevel": 400,
        "xpForNextLevel": 900,
        "streakDays": 3,
        "completedCount": 5,
        "overdueCount": 1,
        "onTimeRate": 0.8,
        "achievements": [
            {
                "key": "FIRST_STEP",
                "emoji": "🎯",
                "name": "Первый шаг",
                "awardedAt": "2026-06-07T00:00:00Z",
            }
        ],
    }


class ProfileRenderTests(unittest.TestCase):
    def test_profile_root_contains_header_and_progress(self) -> None:
        rendered = _render_profile(sample_stats())
        self.assertIn("Профиль", rendered)
        self.assertIn("Уровень 2", rendered)
        self.assertIn("450 / 900 XP", rendered)

    def test_stats_view_contains_expanded_metrics(self) -> None:
        rendered = _render_stats(sample_stats())
        self.assertIn("Статистика", rendered)
        self.assertIn("Выполнено задач", rendered)
        self.assertIn("До следующего уровня", rendered)

    def test_my_achievements_view_shows_progress(self) -> None:
        rendered = _render_achievements(sample_stats())
        self.assertIn("Мои достижения", rendered)
        self.assertIn("(1/7)", rendered)
        self.assertIn("Первый шаг", rendered)

    def test_all_achievements_marks_unlocked_and_locked(self) -> None:
        rendered = _render_all_achievements(sample_stats())
        self.assertIn("Все достижения", rendered)
        self.assertIn("✅ 🎯", rendered)
        self.assertIn("🔒 ⚡", rendered)

    def test_levels_view_marks_current_progress(self) -> None:
        rendered = _render_levels(sample_stats())
        self.assertIn("Уровни", rendered)
        self.assertIn("2. Исполнитель", rendered)
        self.assertIn("3. Специалист", rendered)


class ProfileKeyboardTests(unittest.TestCase):
    def test_main_menu_has_profile_button(self) -> None:
        buttons = [
            (button.text, button.callback_data)
            for row in member_main_keyboard().inline_keyboard
            for button in row
        ]
        self.assertIn(("👤 Профиль", "profile:open"), buttons)

    def test_profile_keyboard_has_navigation(self) -> None:
        callbacks = [
            button.callback_data
            for row in _profile_keyboard().inline_keyboard
            for button in row
        ]
        self.assertIn("profile:stats", callbacks)
        self.assertIn("profile:achievements", callbacks)
        self.assertIn("profile:all_achievements", callbacks)
        self.assertIn("profile:levels", callbacks)
        self.assertIn("member:back", callbacks)

    def test_submenus_have_back_to_profile(self) -> None:
        for keyboard in (_achievements_keyboard(), _stats_keyboard(), _submenu_keyboard()):
            callbacks = [
                button.callback_data
                for row in keyboard.inline_keyboard
                for button in row
            ]
            self.assertIn("profile:open", callbacks)
            self.assertIn("member:back", callbacks)


class BotNotificationEventTests(unittest.TestCase):
    def test_achievement_fields_parse_from_camel_case(self) -> None:
        event = BotNotificationEvent.model_validate(
            {
                "recipientTelegramIds": [1],
                "type": "ACHIEVEMENT",
                "achievementName": "Первый шаг",
                "achievementEmoji": "🎯",
                "xpGained": 50,
                "newTotalXp": 150,
            }
        )

        self.assertEqual("Первый шаг", event.achievement_name)
        self.assertEqual("🎯", event.achievement_emoji)
        self.assertEqual(50, event.xp_gained)
        self.assertEqual(150, event.new_total_xp)


if __name__ == "__main__":
    unittest.main()
