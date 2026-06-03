package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.NotBlank;

public record YouGileCredentialsRequest(
        @NotBlank String login,
        @NotBlank String password
) {}
