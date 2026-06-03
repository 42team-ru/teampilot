package ru.team42.backend.kafka_common.event;

import lombok.Builder;
import lombok.Getter;
import lombok.extern.jackson.Jacksonized;

import java.util.UUID;

@Getter
@Builder
@Jacksonized
public class LlmStatusChangeEvent extends BaseEvent {

    // Internal task ID — LLM references tasks by the ID returned at creation time
    private UUID taskId;
    // Raw external status string (e.g. YouGile column name) OR internal status name
    private String newStatus;
    // Optional: user who triggered the change in Telegram
    private String triggeredByUsername;
}
