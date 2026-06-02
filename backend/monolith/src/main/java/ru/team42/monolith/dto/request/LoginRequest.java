package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record LoginRequest(
        @NotBlank String inviteToken,
        @NotNull Long telegramId,
        String telegramLogin,
        String firstName,
        String lastName
) {}
