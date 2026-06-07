package ru.team42.monolith.event;

import lombok.Getter;
import ru.team42.backend.kafka_common.event.BaseEvent;

@Getter
public class CourseRecommendRequestEvent extends BaseEvent {

    private final String requestId;
    private final String taskId;
    private final String taskTitle;
    private final String taskDescription;
    private final String teamId;

    public CourseRecommendRequestEvent(String requestId, String taskId, String taskTitle, String taskDescription, String teamId) {
        this.requestId = requestId;
        this.taskId = taskId;
        this.taskTitle = taskTitle;
        this.taskDescription = taskDescription;
        this.teamId = teamId;
    }
}
