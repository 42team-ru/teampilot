package ru.team42.monolith.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.enums.TaskLocalStatus;
import ru.team42.monolith.entity.enums.TaskSyncStatus;

import java.time.Instant;
import java.time.LocalDateTime;
import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface TaskRepository extends JpaRepository<Task, UUID> {

    Page<Task> findByTeamId(UUID teamId, Pageable pageable);

    Page<Task> findByTeamIdAndColumnId(UUID teamId, UUID columnId, Pageable pageable);

    Page<Task> findByColumnId(UUID columnId, Pageable pageable);

    Page<Task> findByTeamIdAndLocalStatus(UUID teamId, TaskLocalStatus localStatus, Pageable pageable);

    Page<Task> findByTeamIdAndLocalStatusIn(UUID teamId, Collection<TaskLocalStatus> statuses, Pageable pageable);

    Page<Task> findByAssigneeUserTelegramId(Long telegramId, Pageable pageable);

    Page<Task> findByAssigneeUserTelegramIdAndCompletedFalseAndDeletedFalse(Long telegramId, Pageable pageable);

    Page<Task> findByAssigneeUserTelegramIdAndLocalStatusIn(
            Long telegramId,
            Collection<TaskLocalStatus> statuses,
            Pageable pageable
    );

    Page<Task> findByTeamIdAndAssigneeUserTelegramId(UUID teamId, Long telegramId, Pageable pageable);

    Page<Task> findByTeamIdAndAssigneeUserTelegramIdAndLocalStatusIn(
            UUID teamId,
            Long telegramId,
            Collection<TaskLocalStatus> statuses,
            Pageable pageable
    );

    List<Task> findBySyncStatus(TaskSyncStatus syncStatus);

    Optional<Task> findByTeamIdAndExternalId(UUID teamId, String externalId);

    List<Task> findByTeamIdAndExternalIdIsNotNullAndLocalStatusNotIn(
            UUID teamId, Collection<TaskLocalStatus> excludedStatuses);

    List<Task> findByLocalStatusAndDeadlineBetweenAndDeadlineNotifiedAtIsNull(
            TaskLocalStatus localStatus,
            Instant from,
            Instant to
    );

    @Query("""
            SELECT t FROM Task t
            WHERE t.localStatus = ru.team42.monolith.entity.enums.TaskLocalStatus.ACTIVE
              AND t.assignee IS NOT NULL
              AND NOT EXISTS (
                  SELECT h FROM TaskStatusHistory h
                  WHERE h.task = t
                    AND h.createdAt > :threshold
              )
            """)
    List<Task> findActiveStaleTasksWithAssignee(@Param("threshold") LocalDateTime threshold);
}
