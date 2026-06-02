package ru.team42.backend.s3_common.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

import java.time.Duration;

/**
 * Конфигурация S3/MinIO.
 *
 * Пример application.yml:
 * <pre>{@code
 * app:
 *   s3:
 *     endpoint: http://localhost:9000     # MinIO; для AWS S3 не указывать
 *     access-key: minioadmin
 *     secret-key: minioadmin
 *     region: us-east-1                  # для MinIO любое значение
 *     default-bucket: my-service-bucket
 *     presigned-url-expiry: 15m
 * }</pre>
 */
@Data
@ConfigurationProperties(prefix = "app.s3")
public class S3Properties {

    /** URL эндпоинта MinIO (или кастомного S3-совместимого хранилища). Для AWS S3 не указывать. */
    private String endpoint;

    /**
     * Публичный URL для генерации presigned URL (тот, что увидит браузер).
     * Если не указан — используется {@link #endpoint}.
     * Пример: https://s3.42team.ru
     */
    private String presignedEndpoint;

    /** Access key (AWS Access Key ID или MinIO root user). */
    private String accessKey;

    /** Secret key (AWS Secret Access Key или MinIO root password). */
    private String secretKey;

    /** AWS region. Для MinIO можно указать любое значение, например {@code us-east-1}. */
    private String region = "us-east-1";

    /**
     * Бакет по умолчанию — удобен как константа в сервисах.
     * Не влияет на логику S3Service напрямую.
     */
    private String defaultBucket;

    /** Время жизни presigned URL (upload и download). По умолчанию 15 минут. */
    private Duration presignedUrlExpiry = Duration.ofMinutes(15);
}
