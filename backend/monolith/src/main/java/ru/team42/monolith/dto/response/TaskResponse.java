package ru.team42.monolith.dto.response;

import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.TaskColumn;
import ru.team42.monolith.entity.enums.TaskLocalStatus;
import ru.team42.monolith.entity.enums.TaskSyncStatus;

import java.time.Instant;
import java.time.LocalDateTime;
import java.util.UUID;

public record TaskResponse(
        UUID id,
        UUID teamId,
        String title,
        String description,
        Instant deadline,
        TaskLocalStatus localStatus,
        TaskSyncStatus syncStatus,
        String externalId,
        ColumnInfo column,
        AssigneeInfo assignee,
        AssigneeInfo author,
        LocalDateTime createdAt,
        boolean completed
) {
    public record AssigneeInfo(UUID teamUserId, Long telegramId, String telegramLogin, String firstName, String lastName) {}

    public record ColumnInfo(UUID columnId, String youGileColumnId, String title) {}

    public static TaskResponse from(Task task) {
        return new TaskResponse(
                task.getId(),
                task.getTeam().getId(),
                task.getTitle(),
                task.getDescription(),
                task.getDeadline(),
                task.getLocalStatus(),
                task.getSyncStatus(),
                task.getExternalId(),
                toColumnInfo(task.getColumn()),
                toAssigneeInfo(task.getAssignee()),
                toAssigneeInfo(task.getAuthor()),
                task.getCreatedAt(),
                task.isCompleted()
        );
    }

    private static ColumnInfo toColumnInfo(TaskColumn col) {
        if (col == null) return null;
        return new ColumnInfo(col.getId(), col.getYouGileColumnId(), col.getTitle());
    }

    private static AssigneeInfo toAssigneeInfo(ru.team42.monolith.entity.TeamUser tu) {
        if (tu == null) return null;
        var u = tu.getUser();
        return new AssigneeInfo(tu.getId(), u.getTelegramId(), u.getTelegramLogin(),
                u.getFirstName(), u.getLastName());
    }
}
