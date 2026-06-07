package ru.team42.monolith.dto.response;

import java.time.Instant;

public record ExtensionLoginStartResponse(
        String code,
        Instant expiresAt
) {
}
