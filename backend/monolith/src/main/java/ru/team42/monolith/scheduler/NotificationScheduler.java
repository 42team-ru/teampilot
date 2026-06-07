package ru.team42.monolith.scheduler;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.enums.TaskLocalStatus;
import ru.team42.monolith.repository.TaskRepository;
import ru.team42.monolith.service.CourseEventPublisher;
import ru.team42.monolith.service.NotificationEventPublisher;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class NotificationScheduler {

    private final TaskRepository taskRepository;
    private final NotificationEventPublisher notificationEventPublisher;
    private final CourseEventPublisher courseEventPublisher;

    @Transactional
    @Scheduled(fixedDelay = 300_000)
    public void sendDeadlineReminders() {
        Instant now = Instant.now();
        Instant from = now.plus(115, ChronoUnit.MINUTES);
        Instant to = now.plus(125, ChronoUnit.MINUTES);

        List<Task> tasks = taskRepository.findByLocalStatusAndDeadlineBetweenAndDeadlineNotifiedAtIsNull(
                TaskLocalStatus.ACTIVE, from, to
        );

        log.info("Deadline reminder check: found {} task(s) in window [{}, {}]", tasks.size(), from, to);

        for (Task task : tasks) {
            try {
                task.setDeadlineNotifiedAt(Instant.now());
                taskRepository.save(task);
                notificationEventPublisher.publishDeadlineReminder(task);
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

    @Transactional(readOnly = true)
    @Scheduled(cron = "0 0 * * * *")
    public void sendStaleAlerts() {
        LocalDateTime threshold = LocalDateTime.now().minus(24, ChronoUnit.HOURS);

        List<Task> staleTasks = taskRepository.findActiveStaleTasks(threshold);

        log.info("Stale alert check: found {} stale task(s)", staleTasks.size());

        for (Task task : staleTasks) {
            try {
                notificationEventPublisher.publishStaleAlert(task);
                log.info("Stale alert sent for task {} ('{}')", task.getId(), task.getTitle());
            } catch (Exception e) {
                log.error("Failed to send stale alert for task {}: {}", task.getId(), e.getMessage());
            }
        }
    }
}
