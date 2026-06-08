package ru.team42.monolith.dto.response;

import java.util.UUID;

public record TaskUpdateMessage(
        UUID taskId,
        String title,
        String status,
        String actorName
) {
    public static TaskUpdateMessage created(UUID taskId, String title) {
        return new TaskUpdateMessage(taskId, title, "CREATED", null);
    }

    public static TaskUpdateMessage approved(UUID taskId, String title, String actorName) {
        return new TaskUpdateMessage(taskId, title, "APPROVED", actorName);
    }

    public static TaskUpdateMessage rejected(UUID taskId, String title, String actorName) {
        return new TaskUpdateMessage(taskId, title, "REJECTED", actorName);
    }
}
