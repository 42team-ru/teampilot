package ru.team42.monolith.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.enums.TaskLocalStatus;
import ru.team42.monolith.entity.enums.TaskSyncStatus;

import java.util.Collection;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface TaskRepository extends JpaRepository<Task, UUID> {

    Page<Task> findByTeamId(UUID teamId, Pageable pageable);

    Page<Task> findByTeamIdAndLocalStatus(UUID teamId, TaskLocalStatus localStatus, Pageable pageable);

    Page<Task> findByTeamIdAndLocalStatusIn(UUID teamId, Collection<TaskLocalStatus> statuses, Pageable pageable);

    Page<Task> findByAssigneeUserTelegramId(Long telegramId, Pageable pageable);

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
}
