package ru.team42.monolith.scheduler;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.enums.TaskLocalStatus;
import ru.team42.monolith.event.BotNotificationEvent;
import ru.team42.monolith.repository.TaskRepository;
import ru.team42.monolith.service.CourseEventPublisher;
import ru.team42.monolith.service.NotificationEventPublisher;
import ru.team42.monolith.service.NotificationPolicyService;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class NotificationScheduler {

    private final TaskRepository taskRepository;
    private final NotificationEventPublisher notificationEventPublisher;
    private final CourseEventPublisher courseEventPublisher;
    private final NotificationPolicyService notificationPolicyService;

    @Transactional
    @Scheduled(fixedDelay = 300_000)
    public void sendDeadlineReminders() {
        Instant now = Instant.now();
        Instant to = now.plus(24, ChronoUnit.HOURS);

        List<Task> tasks = taskRepository.findDeadlineReminderCandidates(now, to);

        log.info("Deadline reminder check: found {} candidate task(s) before {}", tasks.size(), to);

        for (Task task : tasks) {
            try {
                if (!notificationPolicyService.shouldSendDeadlineReminder(task, now)) {
                    continue;
                }
                List<Long> recipients = notificationEventPublisher.publishDeadlineReminder(task);
                if (recipients.isEmpty()) {
                    continue;
                }
                notificationPolicyService.recordQueued(task, BotNotificationEvent.TYPE_DEADLINE, recipients, now);
                task.setDeadlineNotifiedAt(now);
                taskRepository.save(task);
                log.info("Deadline reminder sent for task {} ('{}')", task.getId(), task.getTitle());
            } catch (Exception e) {
                log.error("Failed to send deadline reminder for task {}: {}", task.getId(), e.getMessage());
            }
        }
    }

    @Transactional
    @Scheduled(fixedDelay = 1_800_000)
    public void sendCourseRecommendations() {
        Instant now = Instant.now();
        List<Task> tasks = taskRepository.findByCourseRecommendationNeeded(now);

        log.info("Course recommendation check: found {} overdue task(s) without recommendation", tasks.size());

        for (Task task : tasks) {
            try {
                task.setCourseRecommendedAt(now);
                taskRepository.save(task);
                courseEventPublisher.publishCourseRecommendRequest(task);
                log.info("Course recommendation request sent for task {} ('{}')", task.getId(), task.getTitle());
            } catch (Exception e) {
                log.error("Failed to send course recommendation request for task {}: {}", task.getId(), e.getMessage());
            }
        }
    }

    @Transactional
    @Scheduled(cron = "0 0 * * * *")
    public void sendStaleAlerts() {
        Instant now = Instant.now();
        List<Task> staleTasks = taskRepository.findByDeletedFalseAndLocalStatus(TaskLocalStatus.ACTIVE);

        log.info("Stale alert check: found {} active task candidate(s)", staleTasks.size());

        for (Task task : staleTasks) {
            try {
                if (!notificationPolicyService.shouldSendStaleAlert(task, now)) {
                    continue;
                }
                List<Long> recipients = notificationEventPublisher.publishStaleAlert(task);
                if (recipients.isEmpty()) {
                    continue;
                }
                notificationPolicyService.recordQueued(task, BotNotificationEvent.TYPE_STALE, recipients, now);
                log.info("Stale alert sent for task {} ('{}')", task.getId(), task.getTitle());
            } catch (Exception e) {
                log.error("Failed to send stale alert for task {}: {}", task.getId(), e.getMessage());
            }
        }
    }
}
