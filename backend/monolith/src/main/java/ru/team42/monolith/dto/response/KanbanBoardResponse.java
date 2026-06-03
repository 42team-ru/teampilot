package ru.team42.monolith.dto.response;

import ru.team42.monolith.entity.KanbanBoard;
import ru.team42.monolith.entity.KanbanProvider;

import java.time.Instant;
import java.util.UUID;

public record KanbanBoardResponse(
        UUID id,
        String name,
        KanbanProvider provider,
        String externalBoardId,
        boolean active,
        Instant createdAt
) {
    public static KanbanBoardResponse from(KanbanBoard board) {
        return new KanbanBoardResponse(
                board.getId(),
                board.getName(),
                board.getProvider(),
                board.getExternalBoardId(),
                board.isActive(),
                board.getCreatedAt()
        );
    }
}
