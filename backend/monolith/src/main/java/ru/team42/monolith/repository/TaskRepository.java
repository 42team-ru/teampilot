package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.TaskStatus;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface TaskRepository extends JpaRepository<Task, UUID>, JpaSpecificationExecutor<Task> {

    List<Task> findAllByBoardId(UUID boardId);

    List<Task> findAllByCreatorId(UUID creatorId);

    List<Task> findAllByAssigneeId(UUID assigneeId);

    List<Task> findAllByStatus(TaskStatus status);

    Optional<Task> findByExternalTaskId(String externalTaskId);

    // All non-terminal tasks that have an external task ID (i.e. synced to a kanban board).
    // Board is fetched eagerly so it is safe to access outside a transaction (e.g. in the scheduler).
    @Query("""
            SELECT t
            FROM Task t
            JOIN FETCH t.board
            WHERE t.externalTaskId IS NOT NULL AND t.status NOT IN (ru.team42.monolith.entity.TaskStatus.DONE, ru.team42.monolith.entity.TaskStatus.CANCELLED)
            """)
    List<Task> findAllActiveSyncedTasks();
}
