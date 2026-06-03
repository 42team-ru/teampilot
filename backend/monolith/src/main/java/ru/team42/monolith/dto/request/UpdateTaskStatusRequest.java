package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.NotNull;
import ru.team42.monolith.entity.TaskStatus;

import java.util.UUID;

public record UpdateTaskStatusRequest(
        @NotNull TaskStatus status,
        // User performing the change (null = system/LLM)
        UUID changedByUserId
) {}
