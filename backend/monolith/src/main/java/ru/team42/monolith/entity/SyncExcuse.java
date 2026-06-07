package ru.team42.monolith.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.common_data.entity.AbstractEntity;

import java.time.LocalDate;
import java.util.UUID;

@Entity
@Table(name = "sync_excuses")
@Getter
@Setter
@NoArgsConstructor
public class SyncExcuse extends AbstractEntity {

    @Column(name = "telegram_id", nullable = false)
    private Long telegramId;

    @Column(name = "team_id", nullable = false)
    private UUID teamId;

    @Column(name = "reason")
    private String reason;

    @Column(name = "excuse_date", nullable = false)
    private LocalDate excuseDate;
}
