package ru.team42.monolith.service;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;

class GamificationServiceTest {

    @Test
    void levelFromXpUsesConfiguredThresholds() {
        assertEquals(1, GamificationService.levelFromXp(0));
        assertEquals(1, GamificationService.levelFromXp(399));
        assertEquals(2, GamificationService.levelFromXp(400));
        assertEquals(3, GamificationService.levelFromXp(900));
        assertEquals(6, GamificationService.levelFromXp(3600));
        assertEquals(6, GamificationService.levelFromXp(100_000));
    }

    @Test
    void xpFloorsKeepLevelOneAtZero() {
        assertEquals(0, GamificationService.xpForCurrentLevel(1));
        assertEquals(400, GamificationService.xpForNextLevel(1));
        assertEquals(400, GamificationService.xpForCurrentLevel(2));
        assertEquals(900, GamificationService.xpForNextLevel(2));
    }

    @Test
    void levelNamesMatchProductCopy() {
        assertEquals("Новобранец", GamificationService.levelName(1));
        assertEquals("Исполнитель", GamificationService.levelName(2));
        assertEquals("Специалист", GamificationService.levelName(3));
        assertEquals("Профессионал", GamificationService.levelName(4));
        assertEquals("Эксперт", GamificationService.levelName(5));
        assertEquals("Легенда", GamificationService.levelName(6));
    }

    @Test
    void levelHelpersClampOutOfRangeInput() {
        assertEquals(1, GamificationService.levelFromXp(-100));
        assertEquals("Новобранец", GamificationService.levelName(0));
        assertEquals(0, GamificationService.xpForCurrentLevel(0));
        assertEquals(4900, GamificationService.xpForNextLevel(999));
    }
}
