package ru.team42.monolith.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.common_data.entity.AbstractEntity;
import ru.team42.monolith.entity.enums.TaskLocalStatus;
import ru.team42.monolith.entity.enums.TaskSource;
import ru.team42.monolith.entity.enums.TaskStatus;
import ru.team42.monolith.entity.enums.TaskSyncStatus;

import java.time.Instant;

@Entity
@Table(name = "tasks")
@Getter
@Setter
@NoArgsConstructor
public class Task extends AbstractEntity {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "team_id", nullable = false)
    private Team team;

    @Column(name = "title", nullable = false)
    private String title;

    @Column(name = "description", columnDefinition = "TEXT")
    private String description;

    @Column(name = "deadline")
    private Instant deadline;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 30)
    private TaskStatus status = TaskStatus.OPEN;

    @Enumerated(EnumType.STRING)
    @Column(name = "sync_status", nullable = false, length = 30)
    private TaskSyncStatus syncStatus = TaskSyncStatus.PENDING_SYNC;

    /** YouGile task card ID — null until successfully synced */
    @Column(name = "external_id")
    private String externalId; // ID задачи в YouGile

    @Column(name = "external_column_id")
    private String externalColumnId; // ID колонки в которой находиться задача в YouGile

    /** TeamUser who was assigned the task (resolved from LLM event) */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "assignee_id")
    private TeamUser assignee;

    /** TeamUser who created / posted the task */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "author_id")
    private TeamUser author;

    @Enumerated(EnumType.STRING)
    @Column(name = "source", nullable = false, length = 20)
    private TaskSource source = TaskSource.LLM;

    /** Raw YouGile column name — e.g. "В работе", "Готово". Null for LLM-created tasks until first sync. */
    @Column(name = "yougile_status")
    private String yougileStatus;

    @Enumerated(EnumType.STRING)
    @Column(name = "local_status", nullable = false, length = 30)
    private TaskLocalStatus localStatus = TaskLocalStatus.ACTIVE;
}
