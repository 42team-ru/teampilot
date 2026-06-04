package ru.team42.monolith.event;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.*;
import lombok.extern.jackson.Jacksonized;
import ru.team42.backend.kafka_common.event.BaseEvent;

import java.time.Instant;

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

    private Long chatId;

    private String title;

    private String description;

    private Long assigneeTelegramId;

    private Long authorTelegramId;

    private String columnId;

    private Instant deadline;
}
