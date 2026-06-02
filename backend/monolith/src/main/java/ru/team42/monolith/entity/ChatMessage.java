package ru.team42.monolith.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.common_data.entity.AbstractEntity;

import java.time.Instant;

@Entity
@Table(name = "chat_messages")
@Getter
@Setter
@NoArgsConstructor
public class ChatMessage extends AbstractEntity {

    @Column(name = "chat_id", nullable = false)
    private Long chatId;

    @Column(name = "tg_user", nullable = false)
    private String tgUser;

    @Column(name = "text", nullable = false, columnDefinition = "TEXT")
    private String text;

    @Column(name = "message_timestamp", nullable = false)
    private Instant messageTimestamp;

    @Column(name = "user_id")
    private Long userId;
}
