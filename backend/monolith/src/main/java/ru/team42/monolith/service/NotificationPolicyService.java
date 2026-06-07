package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.monolith.entity.NotificationLog;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.enums.TaskLocalStatus;
import ru.team42.monolith.event.BotNotificationEvent;
import ru.team42.monolith.repository.NotificationLogRepository;
import ru.team42.monolith.repository.TaskStatusHistoryRepository;

import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class NotificationPolicyService {

    private static final ZoneId REMINDER_ZONE = ZoneId.of("Europe/Moscow");

    private final NotificationLogRepository notificationLogRepository;
    private final TaskStatusHistoryRepository taskStatusHistoryRepository;

    @Transactional(readOnly = true)
    public boolean shouldSendDeadlineReminder(Task task, Instant now) {
        if (!isActiveTask(task)) {
            return false;
        }
        if (task.getDeadline() == null || task.getDeadline().isBefore(now)) {
            return false;
        }
        Team team = task.getTeam();
        Instant dueAt = task.getDeadline().minus(Math.max(1, team.getDeadlineReminderMinutesBefore()), ChronoUnit.MINUTES);
        if (now.isBefore(dueAt)) {
            return false;
        }
        return canSendByTeamPolicy(task, BotNotificationEvent.TYPE_DEADLINE, now);
    }

    @Transactional(readOnly = true)
    public boolean shouldSendStaleAlert(Task task, Instant now) {
        if (!isActiveTask(task)) {
            return false;
        }
        Team team = task.getTeam();
        LocalDateTime threshold = LocalDateTime.ofInstant(now, REMINDER_ZONE)
                .minus(Math.max(1, team.getStaleReminderHours()), ChronoUnit.HOURS);
        LocalDateTime lastTaskUpdate = task.getUpdatedAt() != null ? task.getUpdatedAt() : task.getCreatedAt();
        if (lastTaskUpdate != null && lastTaskUpdate.isAfter(threshold)) {
            return false;
        }
        if (taskStatusHistoryRepository.existsByTaskIdAndCreatedAtAfter(task.getId(), threshold)) {
            return false;
        }
        return canSendByTeamPolicy(task, BotNotificationEvent.TYPE_STALE, now);
    }

    @Transactional
    public void recordQueued(Task task, String type, List<Long> recipients, Instant now) {
        if (recipients == null || recipients.isEmpty()) {
            return;
        }
        UUID batchId = UUID.randomUUID();
        for (Long recipient : recipients) {
            NotificationLog log = new NotificationLog();
            log.setBatchId(batchId);
            log.setTask(task);
            log.setRecipientTelegramId(recipient);
            log.setType(type);
            log.setChannel("DM");
            log.setStatus("QUEUED");
            log.setSentAt(now);
            notificationLogRepository.save(log);
        }
    }

    private boolean canSendByTeamPolicy(Task task, String type, Instant now) {
        Team team = task.getTeam();
        if (isQuietTime(team, now)) {
            log.info("Notification {} suppressed for task {}: quiet hours", type, task.getId());
            return false;
        }
        Instant todayStart = LocalDate.now(REMINDER_ZONE).atStartOfDay(REMINDER_ZONE).toInstant();
        long remindersToday = notificationLogRepository.countReminderBatchesSince(task.getId(), type, todayStart);
        int maxPerDay = Math.max(1, team.getReminderMaxPerTaskPerDay());
        if (remindersToday >= maxPerDay) {
            log.info(
                    "Notification {} suppressed for task {}: daily limit reached ({}/{})",
                    type,
                    task.getId(),
                    remindersToday,
                    maxPerDay
            );
            return false;
        }
        return true;
    }

    private boolean isActiveTask(Task task) {
        return task != null
                && task.getId() != null
                && !task.isCompleted()
                && !task.isDeleted()
                && task.getLocalStatus() == TaskLocalStatus.ACTIVE;
    }

    private boolean isQuietTime(Team team, Instant now) {
        int startHour = normalizeHour(team.getReminderQuietHoursStart());
        int endHour = normalizeHour(team.getReminderQuietHoursEnd());
        if (startHour == endHour) {
            return false;
        }
        LocalTime current = now.atZone(REMINDER_ZONE).toLocalTime();
        LocalTime start = LocalTime.of(startHour, 0);
        LocalTime end = LocalTime.of(endHour, 0);
        if (start.isBefore(end)) {
            return !current.isBefore(start) && current.isBefore(end);
        }
        return !current.isBefore(start) || current.isBefore(end);
    }

    private int normalizeHour(int hour) {
        if (hour < 0) {
            return 0;
        }
        if (hour > 23) {
            return 23;
        }
        return hour;
    }
}
