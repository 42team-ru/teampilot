package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.dto.response.TeamReportResponse;
import ru.team42.monolith.entity.SickLeaveRecord;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.repository.SickLeaveRecordRepository;
import ru.team42.monolith.repository.TaskRepository;
import ru.team42.monolith.repository.TeamRepository;
import ru.team42.monolith.repository.TeamUserRepository;

import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class TeamReportService {

    private static final int DAILY_HISTORY_DAYS = 7;

    private static final Map<DayOfWeek, String> WEEKDAY_LABELS = Map.of(
            DayOfWeek.MONDAY, "Пн",
            DayOfWeek.TUESDAY, "Вт",
            DayOfWeek.WEDNESDAY, "Ср",
            DayOfWeek.THURSDAY, "Чт",
            DayOfWeek.FRIDAY, "Пт",
            DayOfWeek.SATURDAY, "Сб",
            DayOfWeek.SUNDAY, "Вс"
    );

    private final TeamRepository teamRepository;
    private final TaskRepository taskRepository;
    private final SickLeaveRecordRepository sickLeaveRecordRepository;
    private final TeamUserRepository teamUserRepository;

    @Transactional(readOnly = true)
    public TeamReportResponse buildReport(UUID teamId) {
        Team team = teamRepository.findById(teamId)
                .orElseThrow(() -> AppException.notFound("Team %s not found".formatted(teamId)));

        List<Task> tasks = taskRepository.findByTeamIdAndDeletedFalse(teamId);
        Instant now = Instant.now();

        Map<String, TeamReportResponse.MemberStats> memberStats = new LinkedHashMap<>();
        int totalTasks = 0;
        int completedTasks = 0;
        int activeTasks = 0;
        int overdueTasks = 0;

        LocalDate today = LocalDate.now(ZoneOffset.UTC);
        Map<LocalDate, Integer> dailyCompletedMap = new LinkedHashMap<>();
        for (int i = DAILY_HISTORY_DAYS - 1; i >= 0; i--) {
            dailyCompletedMap.put(today.minusDays(i), 0);
        }

        Map<DayOfWeek, Integer> weekdayMap = new EnumMap<>(DayOfWeek.class);
        for (DayOfWeek day : DayOfWeek.values()) {
            weekdayMap.put(day, 0);
        }

        for (Task task : tasks) {
            String username = displayName(task.getAssignee());
            boolean completed = task.isCompleted();
            boolean overdue = !completed && task.getDeadline() != null && task.getDeadline().isBefore(now);

            totalTasks++;
            if (completed) {
                completedTasks++;
            } else {
                activeTasks++;
                if (overdue) {
                    overdueTasks++;
                }
            }

            if (completed && task.getUpdatedAt() != null) {
                LocalDate completedDate = task.getUpdatedAt().atZone(ZoneOffset.UTC).toLocalDate();
                dailyCompletedMap.computeIfPresent(completedDate, (date, count) -> count + 1);
                weekdayMap.merge(completedDate.getDayOfWeek(), 1, Integer::sum);
            }

            TeamReportResponse.MemberStats prev = memberStats.get(username);
            int prevTotal = prev != null ? prev.totalTasks() : 0;
            int prevCompleted = prev != null ? prev.completedTasks() : 0;
            int prevActive = prev != null ? prev.activeTasks() : 0;
            int prevOverdue = prev != null ? prev.overdueTasks() : 0;

            memberStats.put(username, new TeamReportResponse.MemberStats(
                    username,
                    prevTotal + 1,
                    prevCompleted + (completed ? 1 : 0),
                    prevActive + (completed ? 0 : 1),
                    prevOverdue + (overdue ? 1 : 0)
            ));
        }

        List<TeamReportResponse.DailyCount> dailyCompleted = new ArrayList<>();
        dailyCompletedMap.forEach((date, count) -> dailyCompleted.add(new TeamReportResponse.DailyCount(date, count)));

        List<TeamReportResponse.WeekdayCount> weekdayProductivity = new ArrayList<>();
        for (DayOfWeek day : DayOfWeek.values()) {
            weekdayProductivity.add(new TeamReportResponse.WeekdayCount(WEEKDAY_LABELS.get(day), weekdayMap.get(day)));
        }

        TeamReportResponse.BestPerformer bestPerformer = memberStats.values().stream()
                .filter(member -> member.completedTasks() > 0)
                .max(Comparator.comparingInt(TeamReportResponse.MemberStats::completedTasks))
                .map(member -> new TeamReportResponse.BestPerformer(member.username(), member.completedTasks()))
                .orElse(null);

        List<TeamReportResponse.ExcuseStats> excuseStats = buildExcuseStats(teamId);

        return new TeamReportResponse(
                team.getChatTitle() != null ? team.getChatTitle() : team.getId().toString(),
                now,
                new TeamReportResponse.Totals(totalTasks, completedTasks, activeTasks, overdueTasks),
                List.copyOf(memberStats.values()),
                dailyCompleted,
                weekdayProductivity,
                bestPerformer,
                excuseStats
        );
    }

    private List<TeamReportResponse.ExcuseStats> buildExcuseStats(UUID teamId) {
        LocalDate monthAgo = LocalDate.now(ZoneOffset.UTC).minusMonths(1);
        List<SickLeaveRecord> records = sickLeaveRecordRepository.findByTeamIdAndRecordDateGreaterThanEqual(teamId, monthAgo);
        if (records.isEmpty()) {
            return List.of();
        }

        Map<Long, String> namesByTelegramId = new LinkedHashMap<>();
        for (TeamUser teamUser : teamUserRepository.findByTeamIdWithUser(teamId)) {
            User user = teamUser.getUser();
            if (user != null && user.getTelegramId() != null) {
                namesByTelegramId.put(user.getTelegramId(), displayName(teamUser));
            }
        }

        Map<String, Integer> counts = new LinkedHashMap<>();
        for (SickLeaveRecord record : records) {
            String name = namesByTelegramId.getOrDefault(record.getTelegramId(), "Без имени");
            counts.merge(name, 1, Integer::sum);
        }

        return counts.entrySet().stream()
                .map(entry -> new TeamReportResponse.ExcuseStats(entry.getKey(), entry.getValue()))
                .sorted((a, b) -> Integer.compare(b.count(), a.count()))
                .toList();
    }

    private String displayName(TeamUser teamUser) {
        if (teamUser == null) {
            return "Без исполнителя";
        }
        User user = teamUser.getUser();
        if (user == null) {
            return "Без исполнителя";
        }
        StringBuilder name = new StringBuilder();
        if (user.getFirstName() != null) {
            name.append(user.getFirstName());
        }
        if (user.getLastName() != null) {
            if (!name.isEmpty()) {
                name.append(' ');
            }
            name.append(user.getLastName());
        }
        if (!name.isEmpty()) {
            return name.toString();
        }
        if (user.getTelegramLogin() != null) {
            return "@" + user.getTelegramLogin();
        }
        return "Без имени";
    }
}
