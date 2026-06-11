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

    List<Task> findByAssigneeUserTelegramIdAndCompletedFalseAndDeletedFalseAndLocalStatus(
            Long telegramId, TaskLocalStatus localStatus);

    List<Task> findByDeletedFalseAndLocalStatus(TaskLocalStatus localStatus);

    Page<Task> findByTeamId(UUID teamId, Pageable pageable);

    Page<Task> findByTeamIdAndColumnId(UUID teamId, UUID columnId, Pageable pageable);

    Page<Task> findByColumnId(UUID columnId, Pageable pageable);

    Page<Task> findByColumnIdAndAssigneeUserTelegramId(UUID columnId, Long telegramId, Pageable pageable);

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

    boolean existsByTeamIdAndTitleIgnoreCaseAndLocalStatusIn(
            UUID teamId, String title, Collection<TaskLocalStatus> statuses);

    Optional<Task> findFirstByTeamIdAndTitleIgnoreCaseAndLocalStatusIn(
            UUID teamId, String title, Collection<TaskLocalStatus> statuses);

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
              AND t.completed = false
              AND t.deleted = false
              AND t.deadline IS NOT NULL
              AND t.deadlineNotifiedAt IS NULL
              AND t.deadline >= :from
              AND t.deadline <= :to
            """)
    List<Task> findDeadlineReminderCandidates(@Param("from") Instant from, @Param("to") Instant to);

    @Query("""
            SELECT t FROM Task t
            WHERE t.localStatus = ru.team42.monolith.entity.enums.TaskLocalStatus.ACTIVE
              AND t.deadline IS NOT NULL
              AND t.deadline < :now
              AND t.courseRecommendedAt IS NULL
            """)
    List<Task> findByCourseRecommendationNeeded(@Param("now") Instant now);

    @Query("""
            SELECT t FROM Task t
            WHERE t.localStatus = ru.team42.monolith.entity.enums.TaskLocalStatus.ACTIVE
              AND NOT EXISTS (
                  SELECT h FROM TaskStatusHistory h
                  WHERE h.task = t
                    AND h.createdAt > :threshold
              )
            """)
    List<Task> findActiveStaleTasks(@Param("threshold") LocalDateTime threshold);

    Page<Task> findByColumnIdAndDeletedFalse(UUID columnId, Pageable pageable);

    Page<Task> findByColumnIdAndAssigneeUserTelegramIdAndDeletedFalse(
            UUID columnId, Long telegramId, Pageable pageable);

    Page<Task> findByColumnIdAndCompletedFalseAndDeletedFalse(UUID columnId, Pageable pageable);

    Page<Task> findByColumnIdAndAssigneeUserTelegramIdAndCompletedFalseAndDeletedFalse(
            UUID columnId, Long telegramId, Pageable pageable);

    Page<Task> findByColumnIdAndCompletedTrueAndDeletedFalse(UUID columnId, Pageable pageable);

    Page<Task> findByColumnIdAndAssigneeUserTelegramIdAndCompletedTrueAndDeletedFalse(
            UUID columnId, Long telegramId, Pageable pageable);

    Page<Task> findByTeamIdAndLocalStatusInAndCompletedFalseAndDeletedFalse(
            UUID teamId, Collection<TaskLocalStatus> statuses, Pageable pageable);

    Page<Task> findByTeamIdAndAssigneeUserTelegramIdAndLocalStatusInAndCompletedFalseAndDeletedFalse(
            UUID teamId, Long telegramId, Collection<TaskLocalStatus> statuses, Pageable pageable);

    Page<Task> findByAssigneeUserTelegramIdAndLocalStatusInAndCompletedFalseAndDeletedFalse(
            Long telegramId, Collection<TaskLocalStatus> statuses, Pageable pageable);

    Page<Task> findByTeamIdAndCompletedTrueAndDeletedFalse(UUID teamId, Pageable pageable);

    Page<Task> findByTeamIdAndAssigneeUserTelegramIdAndCompletedTrueAndDeletedFalse(
            UUID teamId, Long telegramId, Pageable pageable);

    Page<Task> findByAssigneeUserTelegramIdAndCompletedTrueAndDeletedFalse(Long telegramId, Pageable pageable);

    long countByAssigneeUserTelegramIdAndCompletedTrueAndDeletedFalse(Long telegramId);

    @Query(
            value = """
                    SELECT COUNT(*)
                    FROM tasks t
                    JOIN team_users tu ON t.assignee_id = tu.id
                    JOIN users u ON tu.user_id = u.id
                    WHERE u.telegram_id = :tid
                      AND t.completed = true
                      AND t.deleted = false
                      AND t.deadline IS NOT NULL
                      AND t.updated_at > t.deadline
                    """,
            nativeQuery = true
    )
    long countOverdueCompleted(@Param("tid") Long telegramId);

    @Query("""
            SELECT COUNT(t) FROM Task t
            WHERE t.assignee.user.telegramId = :tid
              AND t.completed = false
              AND t.deleted = false
              AND t.deadline IS NOT NULL
              AND t.deadline < :now
            """)
    long countStillOverdue(@Param("tid") Long telegramId, @Param("now") Instant now);

    List<Task> findTop10ByAssigneeUserTelegramIdAndCompletedTrueAndDeletedFalseOrderByUpdatedAtDesc(Long telegramId);

    @Query(
            value = """
                    SELECT COUNT(*)
                    FROM tasks t
                    JOIN team_users tu ON t.assignee_id = tu.id
                    JOIN users u ON tu.user_id = u.id
                    WHERE u.telegram_id = :tid
                      AND t.completed = true
                      AND t.deleted = false
                      AND t.deadline IS NOT NULL
                      AND t.updated_at > t.deadline
                      AND t.updated_at >= :since
                    """,
            nativeQuery = true
    )
    long countOverdueCompletedSince(@Param("tid") Long telegramId, @Param("since") LocalDateTime since);

    @Query("""
            SELECT COUNT(t) FROM Task t
            WHERE t.assignee.user.telegramId = :tid
              AND t.completed = false
              AND t.deleted = false
              AND t.deadline IS NOT NULL
              AND t.deadline >= :since
              AND t.deadline < :now
            """)
    long countStillOverdueSince(
            @Param("tid") Long telegramId,
            @Param("since") Instant since,
            @Param("now") Instant now
    );

    @Query("""
        SELECT tu.id, tu.user.firstName, tu.user.lastName, tu.user.telegramLogin, tu.user.telegramId,
               COUNT(t) as openCount,
               SUM(CASE WHEN t.deadline IS NOT NULL AND t.deadline < :now THEN 1L ELSE 0L END) as overdueCount
        FROM Task t
        JOIN t.assignee tu
        WHERE tu.team.id = :teamId
          AND t.completed = false
          AND t.deleted = false
          AND t.localStatus = ru.team42.monolith.entity.enums.TaskLocalStatus.ACTIVE
        GROUP BY tu.id, tu.user.firstName, tu.user.lastName, tu.user.telegramLogin, tu.user.telegramId
        """)
    List<Object[]> findWorkloadByTeamId(@Param("teamId") UUID teamId, @Param("now") Instant now);
}
