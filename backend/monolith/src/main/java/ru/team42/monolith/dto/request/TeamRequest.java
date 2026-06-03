package ru.team42.monolith.dto.request;

public record TeamRequest(
        Long telegramChatId,
        String chatTitle,
        String kanbanId,
        String kanbanApiKey
) {}
