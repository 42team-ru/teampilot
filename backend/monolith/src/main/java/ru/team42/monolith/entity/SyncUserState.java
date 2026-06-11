package ru.team42.monolith.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import ru.team42.monolith.entity.enums.UserSyncStatus;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Entity
@Table(name = "sync_user_states")
@Getter
@Setter
@NoArgsConstructor
public class SyncUserState {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    @Column(name = "id", nullable = false)
    private UUID id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "team_id", nullable = false)
    private SyncSession session;

    @Column(name = "telegram_id")
    private Long telegramId;

    @Column(name = "username")
    private String username;

    @Enumerated(EnumType.STRING)
    @Column(name = "status")
    private UserSyncStatus status;

    @Column(name = "raw_text", columnDefinition = "text")
    private String rawText;

    @Column(name = "request_id", unique = true)
    private String requestId;

    @Column(name = "confirmed_tasks_count")
    private int confirmedTasksCount;

    @Column(name = "pending_tasks_count")
    private int pendingTasksCount;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "confirmed_task_titles", columnDefinition = "jsonb")
    private List<String> confirmedTaskTitles = new ArrayList<>();

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "pending_task_titles", columnDefinition = "jsonb")
    private List<String> pendingTaskTitles = new ArrayList<>();
}
