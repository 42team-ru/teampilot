package ru.team42.monolith.dto.response;

import java.time.Instant;
import java.util.List;

public record UserStatsResponse(
        long completedCount,
        long overdueCount,
        double onTimeRate,
        int streakDays,
        long xp,
        int level,
        String levelName,
        long xpForCurrentLevel,
        long xpForNextLevel,
        List<AchievementDto> achievements
) {
    public record AchievementDto(
            String key,
            String emoji,
            String name,
            Instant awardedAt
    ) {
    }
}
