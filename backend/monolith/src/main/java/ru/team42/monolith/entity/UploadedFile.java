package ru.team42.monolith.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.s3_common.entity.AbstractStoredFileEntity;

@Entity
@Table(name = "uploaded_files")
@Getter
@Setter
@NoArgsConstructor
public class UploadedFile extends AbstractStoredFileEntity {

    @Column(name = "telegram_user_id")
    private Long telegramUserId;

    @Column(name = "telegram_chat_id")
    private Long telegramChatId;

    @Column(name = "telegram_username", length = 255)
    private String telegramUsername;

    @Column(name = "telegram_first_name", length = 255)
    private String telegramFirstName;
}
