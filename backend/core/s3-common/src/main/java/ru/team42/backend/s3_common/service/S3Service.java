package ru.team42.backend.s3_common.service;

import lombok.RequiredArgsConstructor;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.BucketAlreadyExistsException;
import software.amazon.awssdk.services.s3.model.BucketAlreadyOwnedByYouException;
import software.amazon.awssdk.services.s3.model.CreateBucketRequest;
import software.amazon.awssdk.services.s3.model.DeleteObjectRequest;
import software.amazon.awssdk.services.s3.model.HeadBucketRequest;
import software.amazon.awssdk.services.s3.model.HeadObjectRequest;
import software.amazon.awssdk.services.s3.model.NoSuchBucketException;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.GetObjectPresignRequest;
import software.amazon.awssdk.services.s3.presigner.model.PutObjectPresignRequest;

import java.io.InputStream;
import java.time.Duration;

/**
 * Низкоуровневый сервис для операций с S3/MinIO.
 *
 * Все методы принимают явный bucket + key — сервис не привязан
 * к конкретной доменной сущности и работает с любым бакетом.
 *
 * Типичный сценарий загрузки:
 * <pre>{@code
 * // 1. Получить presigned URL для прямой загрузки в S3 с фронтенда
 * String uploadUrl = s3Service.presignUpload("uploads", "files/photo.jpg", "image/jpeg");
 *
 * // 2. Клиент выполняет HTTP PUT на uploadUrl
 *
 * // 3. Сохранить метаданные в Postgres
 * var entity = new PhotoFile();
 * entity.setBucket("uploads");
 * entity.setS3Key("files/photo.jpg");
 * entity.setOriginalFilename("photo.jpg");
 * entity.setContentType("image/jpeg");
 * repository.save(entity);
 * }</pre>
 */
@RequiredArgsConstructor
public class S3Service {

    private final S3Client s3Client;
    private final S3Presigner s3Presigner;
    private final Duration defaultPresignedExpiry;

    /**
     * Создать бакет, если он не существует. Идемпотентно.
     */
    public void ensureBucketExists(String bucket) {
        try {
            s3Client.headBucket(HeadBucketRequest.builder().bucket(bucket).build());
        } catch (NoSuchBucketException e) {
            try {
                s3Client.createBucket(CreateBucketRequest.builder().bucket(bucket).build());
            } catch (BucketAlreadyExistsException | BucketAlreadyOwnedByYouException ignored) {
            }
        }
    }

    /**
     * Загрузить объект напрямую с сервера (server-side upload).
     *
     * @param bucket      имя бакета
     * @param key         ключ объекта
     * @param inputStream поток байт файла
     * @param sizeBytes   размер файла в байтах (обязателен для AWS SDK v2)
     * @param contentType MIME-тип
     */
    public void upload(String bucket, String key, InputStream inputStream, long sizeBytes, String contentType) {
        s3Client.putObject(
                PutObjectRequest.builder()
                        .bucket(bucket)
                        .key(key)
                        .contentType(contentType)
                        .contentLength(sizeBytes)
                        .build(),
                RequestBody.fromInputStream(inputStream, sizeBytes));
    }

    /**
     * Presigned URL для прямой загрузки (HTTP PUT) из клиента в S3.
     *
     * @param bucket      имя бакета
     * @param key         ключ объекта в бакете
     * @param contentType MIME-тип загружаемого файла
     * @param expiry      время жизни URL
     * @return presigned PUT URL
     */
    public String presignUpload(String bucket, String key, String contentType, Duration expiry) {
        var presignRequest = PutObjectPresignRequest.builder()
                .signatureDuration(expiry)
                .putObjectRequest(r -> r
                        .bucket(bucket)
                        .key(key)
                        .contentType(contentType))
                .build();
        return s3Presigner.presignPutObject(presignRequest).url().toString();
    }

    /** Presigned PUT URL с дефолтным временем жизни из {@code app.s3.presigned-url-expiry}. */
    public String presignUpload(String bucket, String key, String contentType) {
        return presignUpload(bucket, key, contentType, defaultPresignedExpiry);
    }

    /**
     * Presigned URL для скачивания объекта (HTTP GET).
     *
     * @param bucket имя бакета
     * @param key    ключ объекта
     * @param expiry время жизни URL
     * @return presigned GET URL
     */
    public String presignDownload(String bucket, String key, Duration expiry) {
        var presignRequest = GetObjectPresignRequest.builder()
                .signatureDuration(expiry)
                .getObjectRequest(r -> r
                        .bucket(bucket)
                        .key(key))
                .build();
        return s3Presigner.presignGetObject(presignRequest).url().toString();
    }

    /** Presigned GET URL с дефолтным временем жизни. */
    public String presignDownload(String bucket, String key) {
        return presignDownload(bucket, key, defaultPresignedExpiry);
    }

    /**
     * Удалить объект из S3. Если объекта нет — не бросает исключение (S3 идемпотентен).
     *
     * @param bucket имя бакета
     * @param key    ключ объекта
     */
    public void delete(String bucket, String key) {
        s3Client.deleteObject(DeleteObjectRequest.builder()
                .bucket(bucket)
                .key(key)
                .build());
    }

    /**
     * Проверить, существует ли объект в S3 (HEAD-запрос).
     *
     * @param bucket имя бакета
     * @param key    ключ объекта
     * @return {@code true} если объект существует
     */
    public boolean exists(String bucket, String key) {
        try {
            s3Client.headObject(HeadObjectRequest.builder()
                    .bucket(bucket)
                    .key(key)
                    .build());
            return true;
        } catch (NoSuchKeyException e) {
            return false;
        }
    }
}
