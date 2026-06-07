package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.TaskStatusHistory;

import java.time.LocalDateTime;
import java.util.List;
import java.util.UUID;

public interface TaskStatusHistoryRepository extends JpaRepository<TaskStatusHistory, UUID> {

    List<TaskStatusHistory> findByTaskIdOrderByCreatedAtAsc(UUID taskId);

    boolean existsByTaskIdAndCreatedAtAfter(UUID taskId, LocalDateTime threshold);
}
