package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.NotNull;

public record TeamRequest(
        @NotNull Long telegramChatId,
        String chatTitle,
        String kanbanId,
        String kanbanApiKey
) {}
