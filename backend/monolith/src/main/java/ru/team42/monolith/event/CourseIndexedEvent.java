package ru.team42.monolith.event;

import lombok.Getter;
import ru.team42.backend.kafka_common.event.BaseEvent;

@Getter
public class CourseIndexedEvent extends BaseEvent {

    private final String courseId;
    private final String title;
    private final String description;
    private final String url;
    private final String teamId;

    public CourseIndexedEvent(String courseId, String title, String description, String url, String teamId) {
        this.courseId = courseId;
        this.title = title;
        this.description = description;
        this.url = url;
        this.teamId = teamId;
    }
}
