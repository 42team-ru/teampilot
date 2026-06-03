package ru.team42.backend.kafka_common.event;

import lombok.Builder;
import lombok.Getter;
import lombok.extern.jackson.Jacksonized;

import java.util.UUID;

@Getter
@Builder
@Jacksonized
public class TaskStatusChangedEvent extends BaseEvent {

    private UUID taskId;
    private String taskTitle;
    private String previousStatus;
    private String newStatus;
    private Long chatId;
    private String changeSource;
}
