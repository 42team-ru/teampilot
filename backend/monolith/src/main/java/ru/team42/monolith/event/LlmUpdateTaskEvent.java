package ru.team42.monolith.event;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.*;
import lombok.extern.jackson.Jacksonized;
import ru.team42.backend.kafka_common.event.BaseEvent;

import java.util.UUID;

@Getter
@Builder
@Jacksonized
@AllArgsConstructor
@NoArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class LlmUpdateTaskEvent extends BaseEvent {

    private UUID taskId;

    private Long assigneeTelegramId;

    private String titleTask;

    private String columnId;

    private String description;

    private Boolean completed;

    private Boolean deleted;

    private DeadlineInfo deadline;

    @Getter
    @Builder
    @Jacksonized
    @AllArgsConstructor
    @NoArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class DeadlineInfo {
        /** Epoch milliseconds */
        private Long deadline;
        /** Epoch milliseconds */
        private Long startDate;
    }
}
