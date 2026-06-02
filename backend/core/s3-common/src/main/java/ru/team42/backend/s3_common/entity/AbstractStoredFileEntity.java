package ru.team42.backend.s3_common.entity;

import jakarta.persistence.Column;
import jakarta.persistence.MappedSuperclass;
import lombok.Getter;
import lombok.Setter;
import lombok.ToString;
import ru.team42.backend.common_data.entity.AbstractEntity;

import java.util.UUID;

/**
 * JPA-метаданные файла, хранящегося в S3/MinIO.
 *
 * Наследуйтесь от этого класса и добавляйте доменные поля.
 * Минимальная Flyway-миграция:
 *
 * <pre>{@code
 * CREATE TABLE stored_files (
 *     id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
 *     bucket         VARCHAR(255) NOT NULL,
 *     s3_key         VARCHAR(1024) NOT NULL UNIQUE,
 *     original_filename VARCHAR(512),
 *     content_type   VARCHAR(255),
 *     size_bytes     BIGINT,
 *     owner_id       UUID,
 *     created_at     TIMESTAMP    NOT NULL,
 *     updated_at     TIMESTAMP
 * );
 * }</pre>
 */
@MappedSuperclass
@Getter
@Setter
@ToString(callSuper = true)
public abstract class AbstractStoredFileEntity extends AbstractEntity {

    /** Имя бакета в S3/MinIO. */
    @Column(name = "bucket", nullable = false, length = 255)
    private String bucket;

    /**
     * Уникальный ключ объекта в бакете (например, {@code uploads/2024/report.pdf}).
     * Используется во всех операциях S3.
     */
    @Column(name = "s3_key", nullable = false, length = 1024, unique = true)
    private String s3Key;

    /** Оригинальное имя файла, переданное пользователем. */
    @Column(name = "original_filename", length = 512)
    private String originalFilename;

    /** MIME-тип (например, {@code image/jpeg}). */
    @Column(name = "content_type", length = 255)
    private String contentType;

    /** Размер файла в байтах. Может быть null до завершения загрузки. */
    @Column(name = "size_bytes")
    private Long sizeBytes;

    /**
     * UUID владельца файла (идентификатор пользователя из JWT-токена).
     * Nullable — для публичных объектов без привязки к пользователю.
     */
    @Column(name = "owner_id")
    private UUID ownerId;
}
