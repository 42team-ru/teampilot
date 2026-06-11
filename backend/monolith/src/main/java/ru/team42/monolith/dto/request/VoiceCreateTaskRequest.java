package ru.team42.monolith.dto.request;

import java.time.Instant;
import java.util.UUID;

/** Тело запроса на создание задачи голосовой командой ассистента. */
public record VoiceCreateTaskRequest(
        UUID teamId,
        String title,
        String assigneeName,
        Instant deadline,
        String description
) {
}
