package ru.team42.monolith.dto.response;

import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.entity.User;

import java.time.Instant;

/**
 * Краткое представление задачи для голосового ассистента — только то, что бот
 * проговаривает вслух: название, исполнитель, дедлайн, колонка.
 */
public record TaskBriefResponse(
        String title,
        String assignee,
        Instant deadline,
        String column,
        boolean completed
) {
    public static TaskBriefResponse from(Task task) {
        return new TaskBriefResponse(
                task.getTitle(),
                displayName(task.getAssignee()),
                task.getDeadline(),
                task.getColumn() != null ? task.getColumn().getTitle() : null,
                task.isCompleted()
        );
    }

    static String displayName(TeamUser tu) {
        if (tu == null) return null;
        User u = tu.getUser();
        String first = u.getFirstName();
        String last = u.getLastName();
        String full = ((first != null ? first : "") + " " + (last != null ? last : "")).trim();
        if (!full.isBlank()) return full;
        return u.getTelegramLogin();
    }
}
