package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.KanbanBoard;

import java.util.List;
import java.util.UUID;

public interface KanbanBoardRepository extends JpaRepository<KanbanBoard, UUID> {

    List<KanbanBoard> findAllByActiveTrue();
}
