package ru.team42.monolith.dto.request;

public record UpdateTeamRequest(
        Long telegramChatId,
        String chatTitle,
        String kanbanId,
        String kanbanApiKey
) {}
