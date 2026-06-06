package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.TaskColumn;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface TaskColumnRepository extends JpaRepository<TaskColumn, UUID> {

    Optional<TaskColumn> findByTeamIdAndYouGileColumnId(UUID teamId, String youGileColumnId);

    List<TaskColumn> findByTeamId(UUID teamId);

}
