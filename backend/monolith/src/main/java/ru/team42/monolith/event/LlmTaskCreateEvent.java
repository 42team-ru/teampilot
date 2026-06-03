package ru.team42.monolith.event;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.Instant;

/**
 * Входящее кфка событие от воркера
 */
@Getter
@Setter
@NoArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class LlmTaskCreateEvent {

    private Long chatId;

    private String title;

    private String description;

    private Long assigneeTelegramId;

    private Long authorTelegramId;

    private Instant deadline;
}
