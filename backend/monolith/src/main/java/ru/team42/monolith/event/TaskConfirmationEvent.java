package ru.team42.monolith.event;

import lombok.Getter;
import ru.team42.backend.kafka_common.event.BaseEvent;

import java.time.Instant;
import java.util.UUID;

@Getter
public class TaskConfirmationEvent extends BaseEvent {

    private final UUID taskId;
    private final Long chatId;
    private final String title;
    private final String description;
    private final String assigneeUsername;
    private final Instant deadline;
    private final boolean autoConfirmed;

    public TaskConfirmationEvent(UUID taskId, Long chatId, String title,
                                 String description, String assigneeUsername,
                                 Instant deadline, boolean autoConfirmed) {
        this.taskId = taskId;
        this.chatId = chatId;
        this.title = title;
        this.description = description;
        this.assigneeUsername = assigneeUsername;
        this.deadline = deadline;
        this.autoConfirmed = autoConfirmed;
    }
}
