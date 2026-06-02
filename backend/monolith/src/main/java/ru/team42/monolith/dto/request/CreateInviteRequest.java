package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.NotNull;

public record CreateInviteRequest(
        @NotNull Long creatorTelegramId,
        String createdBy
) {}
