package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.time.Instant;
import java.util.UUID;

public record CreateUserTaskRequest(
        @NotNull UUID teamId,
        @NotBlank String title,
        String description,
        Instant deadline,
        UUID columnId,
        UUID assigneeTeamUserId
) {}
