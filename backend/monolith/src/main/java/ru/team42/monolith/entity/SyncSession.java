package ru.team42.monolith.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Entity
@Table(name = "sync_sessions")
@Getter
@Setter
@NoArgsConstructor
public class SyncSession {

    @Id
    @Column(name = "team_id", nullable = false)
    private UUID teamId;

    @Column(name = "chat_id", unique = true)
    private Long chatId;

    @Column(name = "started_at")
    private Instant startedAt;

    @OneToMany(mappedBy = "session", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    private List<SyncUserState> userStates = new ArrayList<>();
}
