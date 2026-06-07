package ru.team42.monolith.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.common_data.entity.AbstractEntity;

import java.time.Instant;

@Entity
@Table(
        name = "user_achievements",
        uniqueConstraints = @UniqueConstraint(
                name = "uq_user_achievements_user_key",
                columnNames = {"user_id", "achievement_key"}
        )
)
@Getter
@Setter
@NoArgsConstructor
public class UserAchievement extends AbstractEntity {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(name = "achievement_key", nullable = false, length = 80)
    private String achievementKey;

    @Column(name = "awarded_at", nullable = false)
    private Instant awardedAt;
}
