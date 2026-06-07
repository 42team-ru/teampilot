package ru.team42.monolith.kafka.consumer;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.entity.Course;
import ru.team42.monolith.event.BotNotificationEvent.CourseInfo;
import ru.team42.monolith.event.CourseRecommendResultEvent;
import ru.team42.monolith.repository.CourseRepository;
import ru.team42.monolith.service.NotificationEventPublisher;
import ru.team42.monolith.repository.TaskRepository;

import java.util.List;
import java.util.UUID;

@Slf4j
@Component
@RequiredArgsConstructor
public class CourseRecommendConsumer {

    private final CourseRepository courseRepository;
    private final TaskRepository taskRepository;
    private final NotificationEventPublisher notificationEventPublisher;

    @KafkaListener(topics = KafkaTopics.COURSES_RECOMMEND_RESULT)
    public void consume(CourseRecommendResultEvent event) {
        log.info("Received courses.recommend.result for taskId={} courses={}",
                event.getTaskId(), event.getCourseIds());

        if (event.getCourseIds() == null || event.getCourseIds().isEmpty()) {
            log.info("No courses recommended for taskId={}, skipping notification", event.getTaskId());
            return;
        }

        List<UUID> uuids = event.getCourseIds().stream()
                .map(id -> {
                    try {
                        return UUID.fromString(id);
                    } catch (IllegalArgumentException e) {
                        log.warn("Invalid course UUID in recommendation result: {}", id);
                        return null;
                    }
                })
                .filter(id -> id != null)
                .toList();

        if (uuids.isEmpty()) {
            log.warn("No valid course UUIDs in recommendation for taskId={}", event.getTaskId());
            return;
        }

        List<Course> courses = courseRepository.findByIdIn(uuids);
        if (courses.isEmpty()) {
            log.warn("No courses found in DB for taskId={} courseIds={}", event.getTaskId(), event.getCourseIds());
            return;
        }

        List<CourseInfo> courseInfos = courses.stream()
                .map(c -> new CourseInfo(c.getId().toString(), c.getTitle(), c.getUrl(), c.getDescription()))
                .toList();

        try {
            UUID taskId = UUID.fromString(event.getTaskId());
            taskRepository.findById(taskId).ifPresentOrElse(
                    task -> notificationEventPublisher.publishCourseRecommendation(task, courseInfos),
                    () -> log.warn("Task {} not found for course recommendation notification", event.getTaskId())
            );
        } catch (IllegalArgumentException e) {
            log.error("Invalid task UUID in recommendation result: {}", event.getTaskId());
        }
    }
}
