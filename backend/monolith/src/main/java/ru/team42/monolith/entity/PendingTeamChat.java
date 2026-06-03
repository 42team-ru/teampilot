package ru.team42.monolith.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.Index;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.common_data.entity.AbstractEntity;
import ru.team42.monolith.entity.enums.PendingTeamChatStatus;

import java.time.Instant;

@Entity
@Table(
        name = "pending_team_chats",
        uniqueConstraints = @UniqueConstraint(name = "uq_pending_team_chats_telegram_chat_id", columnNames = "telegram_chat_id"),
        indexes = {
                @Index(name = "idx_pending_team_chats_added_by_status", columnList = "added_by_user_id,status"),
                @Index(name = "idx_pending_team_chats_status", columnList = "status")
        }
)
@Getter
@Setter
@NoArgsConstructor
public class PendingTeamChat extends AbstractEntity {

    @Column(name = "telegram_chat_id", nullable = false, unique = true)
    private Long telegramChatId;

    @Column(name = "chat_title", nullable = false)
    private String chatTitle;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "added_by_user_id", nullable = false)
    private User addedBy;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false, length = 50)
    private PendingTeamChatStatus status = PendingTeamChatStatus.PENDING;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "linked_team_id")
    private Team linkedTeam;

    @Column(name = "linked_at")
    private Instant linkedAt;

    @Column(name = "last_seen_at")
    private Instant lastSeenAt;
}
