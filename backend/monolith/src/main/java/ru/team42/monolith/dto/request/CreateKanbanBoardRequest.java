package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import ru.team42.monolith.entity.KanbanProvider;

import java.util.UUID;

public record CreateKanbanBoardRequest(
        @NotBlank String name,
        @NotNull KanbanProvider provider,
        @NotBlank String externalBoardId,
        // API token for external system (required for integration)
        String accessToken,
        // JSON: {"external_status": "INTERNAL_STATUS"} — optional, can be set later
        String statusMappingsJson,
        // Link to an existing Group (optional)
        UUID groupId
) {}
