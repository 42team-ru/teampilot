package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.NotNull;

public record LoginRequest(
        @NotNull Long telegramId,
        String telegramLogin,
        String firstName,
        String lastName,
        String position
) {}
