package ru.team42.monolith.dto.response;

import ru.team42.monolith.entity.User;

import java.util.UUID;

public record AuthResponse(
        UUID userId,
        Long telegramId,
        User.Role role
) {}
