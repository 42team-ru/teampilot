package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import ru.team42.monolith.entity.TaskPriority;

import java.time.Instant;
import java.util.UUID;

public record CreateTaskRequest(
        @NotNull UUID creatorId,
        UUID assigneeId,
        @NotBlank String title,
        String description,
        Instant deadline,
        TaskPriority priority,
        UUID boardId,
        Long chatId,
        String sourceContext
) {}
