package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record CreateUserRequest(
        @NotNull Long telegramId,
        String telegramLogin,
        @NotBlank String firstName,
        String lastName
) {}
