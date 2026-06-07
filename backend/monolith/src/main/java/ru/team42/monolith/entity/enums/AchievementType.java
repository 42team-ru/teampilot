package ru.team42.monolith.entity.enums;

import lombok.Getter;

@Getter
public enum AchievementType {
    FIRST_STEP("🎯", "Первый шаг", "Первая выполненная задача", 50),
    LIGHTNING("⚡", "Молния", "Задача закрыта быстрее половины отведенного времени", 100),
    EARLY_BIRD("🏃", "Ранний финиш", "Задача закрыта минимум за 24 часа до дедлайна", 75),
    WEEK_STREAK("🔥", "Неделя в огне", "Стрик достиг 7 дней", 100),
    SNIPER("🎯", "Снайпер", "10 задач подряд закрыты в срок", 150),
    MOUNTAIN("🏔️", "Гора задач", "50 задач выполнено", 200),
    CLEAN_MONTH("❄️", "Чистый месяц", "Нет просроченных задач за последние 30 дней", 200);

    private final String emoji;
    private final String name;
    private final String description;
    private final int xpReward;

    AchievementType(String emoji, String name, String description, int xpReward) {
        this.emoji = emoji;
        this.name = name;
        this.description = description;
        this.xpReward = xpReward;
    }
}
