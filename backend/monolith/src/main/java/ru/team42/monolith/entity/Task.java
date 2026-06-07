package ru.team42.monolith.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.JoinTable;
import jakarta.persistence.ManyToMany;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import ru.team42.backend.common_data.entity.AbstractEntity;
import ru.team42.monolith.entity.enums.TaskLocalStatus;
import ru.team42.monolith.entity.enums.TaskSource;
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

    @Column(name = "deleted")
    private boolean deleted = false;

    @Column(name = "completed")
    private boolean completed = false;

    @Enumerated(EnumType.STRING)
    @Column(name = "sync_status", nullable = false, length = 30)
    private TaskSyncStatus syncStatus = TaskSyncStatus.PENDING_SYNC;

    /** YouGile task card ID — null until successfully synced */
    @Column(name = "external_id")
    private String externalId;

    /** Колонка канбана, к которой относится задача */
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "column_id")
    private TaskColumn column;

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

    @Enumerated(EnumType.STRING)
    @Column(name = "local_status", nullable = false, length = 30)
    private TaskLocalStatus localStatus = TaskLocalStatus.PENDING_APPROVAL;

    @Column(name = "deadline_notified_at")
    private Instant deadlineNotifiedAt;

    @Column(name = "course_recommended_at")
    private Instant courseRecommendedAt;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "stickers", columnDefinition = "jsonb")
    private Map<String, String> stickers;

    @ManyToMany(fetch = FetchType.LAZY)
    @JoinTable(
            name = "task_source_messages",
            joinColumns = @JoinColumn(name = "task_id"),
            inverseJoinColumns = @JoinColumn(name = "message_id")
    )
    private List<ChatMessage> sourceMessages = new ArrayList<>();
}
