package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.util.UUID;

public record YouGileConnectRequest(
        @NotBlank String login,
        @NotBlank String password,
        @NotBlank String companyId,
        @NotNull UUID teamId
) {}
