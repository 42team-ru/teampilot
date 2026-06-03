package ru.team42.monolith.dto.response;

import java.util.UUID;

public record GroupResponse(
        UUID id,
        Long chatId,
        String chatTitle,
        String yougileBoardId,
        boolean active
) {}
