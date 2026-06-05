package ru.team42.monolith.event;

import lombok.Getter;
import ru.team42.backend.kafka_common.event.BaseEvent;

import java.time.Instant;
import java.util.UUID;

@Getter
public class TaskStateEvent extends BaseEvent {

    public enum Type { CREATED, CANCELLED, COLUMN_CHANGED }

    private final UUID taskId;
    private final Long chatId;
    private final Type type;
    private final String title;
    private final String columnTitle;
    private final String assigneeUsername;
    private final Instant deadline;

    public TaskStateEvent(UUID taskId, Long chatId, Type type, String title,
                          String columnTitle, String assigneeUsername, Instant deadline) {
        this.taskId = taskId;
        this.chatId = chatId;
        this.type = type;
        this.title = title;
        this.columnTitle = columnTitle;
        this.assigneeUsername = assigneeUsername;
        this.deadline = deadline;
    }
}
