package ru.team42.monolith.dto.response;

import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.TaskPriority;
import ru.team42.monolith.entity.TaskStatus;

import java.time.Instant;
import java.util.UUID;

public record TaskResponse(
        UUID id,
        UUID boardId,
        UUID creatorId,
        String creatorName,
        UUID assigneeId,
        String assigneeName,
        String title,
        String description,
        Instant deadline,
        boolean overdue,
        TaskStatus status,
        TaskPriority priority,
        String externalTaskId,
        String externalStatus,
        Long chatId,
        Instant createdAt,
        Instant updatedAt
) {
    public static TaskResponse from(Task task) {
        boolean overdue = task.getDeadline() != null && task.getDeadline().isBefore(Instant.now())
                && !task.getStatus().isTerminal();
        return new TaskResponse(
                task.getId(),
                task.getBoard() != null ? task.getBoard().getId() : null,
                task.getCreator().getId(),
                fullName(task.getCreator().getFirstName(), task.getCreator().getLastName()),
                task.getAssignee() != null ? task.getAssignee().getId() : null,
                task.getAssignee() != null
                        ? fullName(task.getAssignee().getFirstName(), task.getAssignee().getLastName())
                        : null,
                task.getTitle(),
                task.getDescription(),
                task.getDeadline(),
                overdue,
                task.getStatus(),
                task.getPriority(),
                task.getExternalTaskId(),
                task.getExternalStatus(),
                task.getChatId(),
                task.getCreatedAt(),
                task.getUpdatedAt()
        );
    }

    private static String fullName(String first, String last) {
        if (first == null && last == null) return null;
        return (first != null ? first : "") + (last != null ? " " + last : "");
    }
}
