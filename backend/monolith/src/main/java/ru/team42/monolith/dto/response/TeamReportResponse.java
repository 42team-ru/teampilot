package ru.team42.monolith.dto.response;

import java.time.Instant;
import java.time.LocalDate;
import java.util.List;

public record TeamReportResponse(
        String teamName,
        Instant generatedAt,
        Totals totals,
        List<MemberStats> members,
        List<DailyCount> dailyCompleted,
        List<WeekdayCount> weekdayProductivity,
        BestPerformer bestPerformer,
        List<ExcuseStats> excuseStats
) {
    public record Totals(
            int totalTasks,
            int completedTasks,
            int activeTasks,
            int overdueTasks
    ) {
    }

    public record MemberStats(
            String username,
            int totalTasks,
            int completedTasks,
            int activeTasks,
            int overdueTasks
    ) {
    }

    public record DailyCount(
            LocalDate date,
            int count
    ) {
    }

    public record WeekdayCount(
            String day,
            int count
    ) {
    }

    public record BestPerformer(
            String username,
            int completedTasks
    ) {
    }

    public record ExcuseStats(
            String username,
            int count
    ) {
    }
}
