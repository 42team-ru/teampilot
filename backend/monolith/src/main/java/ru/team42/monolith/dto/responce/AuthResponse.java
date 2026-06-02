package ru.team42.monolith.dto.responce;

import java.util.UUID;

public record AuthResponse(
        UUID userId,
        Long telegramId,
        String role
) {}
