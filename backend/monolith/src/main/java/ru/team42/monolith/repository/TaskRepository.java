package ru.team42.monolith.repository;

import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.enums.TaskStatus;
import ru.team42.monolith.entity.enums.TaskSyncStatus;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface TaskRepository extends JpaRepository<Task, UUID> {

    Page<Task> findByTeamId(UUID teamId, Pageable pageable);

    Page<Task> findByTeamIdAndStatus(UUID teamId, TaskStatus status, Pageable pageable);

    List<Task> findBySyncStatus(TaskSyncStatus syncStatus);

    Optional<Task> findByTeamIdAndExternalId(UUID teamId, String externalId);
}
