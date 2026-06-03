package ru.team42.monolith.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.common_data.entity.AbstractEntity;

@Entity
@Table(name = "kanban_boards")
@Getter
@Setter
@NoArgsConstructor
public class KanbanBoard extends AbstractEntity {

    @Column(name = "name", nullable = false)
    private String name;

    @Enumerated(EnumType.STRING)
    @Column(name = "provider", nullable = false, length = 50)
    private KanbanProvider provider;

    @Column(name = "external_board_id", nullable = false, length = 512)
    private String externalBoardId;

    @Column(name = "access_token", length = 1024)
    private String accessToken;

    // JSON: {"external_status_name": "INTERNAL_TASK_STATUS_ENUM", ...}
    // Example for YouGile: {"В работе": "IN_PROGRESS", "Готово": "DONE", "Backlog": "OPEN"}
    @Column(name = "status_mappings", columnDefinition = "TEXT")
    private String statusMappingsJson;

    @Column(name = "active", nullable = false)
    private boolean active = true;
}
