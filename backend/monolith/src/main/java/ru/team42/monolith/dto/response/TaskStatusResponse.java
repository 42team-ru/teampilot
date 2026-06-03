package ru.team42.monolith.dto.response;

import ru.team42.monolith.entity.TaskStatus;

import java.util.UUID;

public record TaskStatusResponse(
        UUID taskId,
        TaskStatus status,
        String externalStatus
) {}
