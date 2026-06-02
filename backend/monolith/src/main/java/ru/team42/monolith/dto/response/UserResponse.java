package ru.team42.monolith.dto.response;

import java.util.UUID;

public record UserResponse(
        UUID userId,
        Long telegramId,
        String role,
        boolean yougileLinked,
        String yougileDisplayName
) {}
