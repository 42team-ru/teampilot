package ru.team42.monolith.dto.request;

public record GroupRequest(
        Long chatId,
        String chatTitle,
        Long addedByTelegramId,
        String yougileToken,
        String yougileBoardId
) {}
