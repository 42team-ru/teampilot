package ru.team42.monolith.dto.response;

import ru.team42.monolith.entity.TaskColumn;

import java.util.UUID;

public record TaskColumnResponse(UUID id, String title) {
    public static TaskColumnResponse from(TaskColumn col) {
        return new TaskColumnResponse(col.getId(), col.getTitle());
    }
}
