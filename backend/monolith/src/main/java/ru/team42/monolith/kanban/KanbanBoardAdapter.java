package ru.team42.monolith.kanban;

import ru.team42.monolith.entity.KanbanBoard;
import ru.team42.monolith.entity.KanbanProvider;
import ru.team42.monolith.entity.Task;

import java.util.List;
import java.util.Map;
import java.util.Optional;

public interface KanbanBoardAdapter {

    KanbanProvider supports();

    // Creates task in external system. Returns external task ID on success.
    Optional<String> createTask(KanbanBoard board, Task task);

    // Returns current raw status string from external system (e.g. YouGile column name).
    Optional<String> getExternalStatus(KanbanBoard board, String externalTaskId);

    // Updates the task status in external system using an external status string.
    void updateExternalStatus(KanbanBoard board, String externalTaskId, String externalStatus);

    // Batch fetch: externalTaskId → current external status. Used by scheduler.
    Map<String, String> getExternalStatuses(KanbanBoard board, List<String> externalTaskIds);
}
