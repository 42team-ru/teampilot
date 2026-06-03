package ru.team42.monolith.dto.response;

import java.time.Instant;

public record InviteResponse(
        String token,
        Instant expiresAt,
        String inviteUrl
) {}
