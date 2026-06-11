package ru.team42.monolith.event;

import lombok.Getter;
import ru.team42.backend.kafka_common.event.BaseEvent;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Getter
public class TaskConfirmationEvent extends BaseEvent {

    private final UUID taskId;
    private final List<Long> recipientTelegramIds;
    private final String title;
    private final String description;
    private final String assigneeUsername;
    private final Instant deadline;
    private final boolean autoConfirmed;
    private final String columnTitle;

    /** Существующая задача — подтверждение создания/статуса */
    public TaskConfirmationEvent(UUID taskId, List<Long> recipientTelegramIds, String title,
                                 String description, String assigneeUsername,
                                 Instant deadline, boolean autoConfirmed, String columnTitle) {
        this.taskId = taskId;
        this.recipientTelegramIds = recipientTelegramIds;
        this.title = title;
        this.description = description;
        this.assigneeUsername = assigneeUsername;
        this.deadline = deadline;
        this.autoConfirmed = autoConfirmed;
        this.columnTitle = columnTitle;
    }
}
