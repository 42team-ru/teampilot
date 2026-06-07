package ru.team42.monolith.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.AbstractEventPublisher;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.entity.Course;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.enums.CourseScope;
import ru.team42.monolith.event.CourseIndexedEvent;
import ru.team42.monolith.event.CourseRecommendRequestEvent;

import java.util.UUID;

@Slf4j
@Component
public class CourseEventPublisher extends AbstractEventPublisher {

    public void publishCourseIndexed(Course course) {
        String teamId = course.getScope() == CourseScope.GLOBAL
                ? "GLOBAL"
                : course.getTeam().getId().toString();
        CourseIndexedEvent event = new CourseIndexedEvent(
                course.getId().toString(),
                course.getTitle(),
                course.getDescription(),
                course.getUrl(),
                teamId
        );
        send(KafkaTopics.COURSES_INDEXED, course.getId().toString(), event);
        log.debug("Published courses.indexed for courseId={}", course.getId());
    }

    public void publishCourseRecommendRequest(Task task) {
        String requestId = UUID.randomUUID().toString();
        CourseRecommendRequestEvent event = new CourseRecommendRequestEvent(
                requestId,
                task.getId().toString(),
                task.getTitle(),
                task.getDescription(),
                task.getTeam().getId().toString()
        );
        send(KafkaTopics.COURSES_RECOMMEND_REQUEST, requestId, event);
        log.debug("Published courses.recommend.request for taskId={}", task.getId());
    }
}
