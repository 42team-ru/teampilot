package ru.team42.monolith.dto.request;

import java.time.Instant;
import java.util.UUID;

public record UpdateTaskRequest(
        String title,
        String description,
        Instant deadline,
        UUID columnId,
        UUID assigneeTeamUserId
) {}
