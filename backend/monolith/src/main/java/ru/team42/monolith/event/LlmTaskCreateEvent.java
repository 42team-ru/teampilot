package ru.team42.monolith.event;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.*;
import lombok.extern.jackson.Jacksonized;
import ru.team42.backend.kafka_common.event.BaseEvent;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Входящее кфка событие от воркера
 */
@Getter
@Builder
@Jacksonized
@AllArgsConstructor
@NoArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class LlmTaskCreateEvent extends BaseEvent {

    private String teamId;

    private String title;

    private String description;

    private Long assigneeId;

    private String columnId;

    private Instant deadline;

    private float confidence;

    private List<UUID> sourceMessageIds;

    private Map<String, String> stickers;
}
