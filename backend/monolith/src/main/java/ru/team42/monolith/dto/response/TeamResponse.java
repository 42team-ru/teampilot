package ru.team42.monolith.dto.response;

import java.util.UUID;

public record TeamResponse(
        UUID id,
        Long telegramChatId,
        String chatTitle,
        String kanbanId,
        boolean active
) {}
