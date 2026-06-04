package ru.team42.monolith.dto.response;

import ru.team42.monolith.entity.enums.SystemRole;

import java.util.UUID;

public record TelegramAuthResponse(
        UUID userId,
        Long telegramId,
        SystemRole systemRole,
        String token
) {}
