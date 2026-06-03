package ru.team42.monolith.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.common_data.entity.AbstractEntity;

@Entity
@Table(
        name = "chat_groups",
        uniqueConstraints = @UniqueConstraint(name = "uq_chat_groups_chat_id", columnNames = "chat_id")
)
@Getter
@Setter
@NoArgsConstructor
public class Group extends AbstractEntity {

    @Column(name = "chat_id", nullable = false, unique = true)
    private Long chatId;

    @Column(name = "chat_title")
    private String chatTitle;

    @Column(name = "added_by_telegram_id", nullable = false)
    private Long addedByTelegramId;

    @Column(name = "yougile_token", nullable = false, length = 512)
    private String yougileToken;

    @Column(name = "yougile_board_id", nullable = false)
    private String yougileBoardId;

    @Column(name = "active", nullable = false)
    private boolean active = true;
}
