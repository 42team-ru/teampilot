package ru.team42.monolith.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.common_data.entity.AbstractEntity;

@Entity
@Table(
        name = "users",
        uniqueConstraints = @UniqueConstraint(name = "uq_users_telegram_id", columnNames = "telegram_id")
)
@Getter
@Setter
@NoArgsConstructor
public class User extends AbstractEntity {

    @Column(name = "telegram_id", nullable = false, unique = true)
    private Long telegramId;

    @Column(name = "telegram_login", length = 100)
    private String telegramLogin;

    @Column(name = "first_name", length = 100)
    private String firstName;

    @Column(name = "last_name", length = 100)
    private String lastName;

    @Enumerated(EnumType.STRING)
    @Column(name = "role", nullable = false, length = 50)
    private Role role = Role.USER;

    @Column(name = "position")
    private String position;

    @Column(name = "yougile_user_id")
    private String yougileUserId;

    @Column(name = "yougile_display_name")
    private String yougileDisplayName;

    public enum Role {
        USER,
        ADMIN,
        SYSTEM_ADMIN
    }
}
