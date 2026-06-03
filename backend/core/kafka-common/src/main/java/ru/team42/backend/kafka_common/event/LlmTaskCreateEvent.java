package ru.team42.backend.kafka_common.event;

import lombok.Builder;
import lombok.Getter;
import lombok.extern.jackson.Jacksonized;

import java.time.Instant;

@Getter
@Builder
@Jacksonized
public class LlmTaskCreateEvent extends BaseEvent {

    private Long chatId;
    private String title;
    private String description;
    private String assigneeUsername;
    private Instant deadline;
    private String sourceContext;
}
