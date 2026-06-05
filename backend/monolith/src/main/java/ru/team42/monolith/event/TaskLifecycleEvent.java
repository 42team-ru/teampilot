package ru.team42.monolith.event;

import lombok.Getter;
import ru.team42.backend.kafka_common.event.BaseEvent;

import java.util.UUID;

@Getter
public class TaskLifecycleEvent extends BaseEvent {

    public enum Type { CONFIRMED, UPDATED, CANCELLED }

    private final UUID taskId;
    private final UUID teamId;
    private final Type type;
    private final String title;
    private final String description;

    public TaskLifecycleEvent(UUID taskId, UUID teamId, Type type, String title, String description) {
        this.taskId = taskId;
        this.teamId = teamId;
        this.type = type;
        this.title = title;
        this.description = description;
    }
}
