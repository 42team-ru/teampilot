package ru.team42.monolith.event;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Builder;
import lombok.Getter;
import ru.team42.backend.kafka_common.event.BaseEvent;

import java.time.Instant;

@Getter
@Builder
public class FileUploadedEvent extends BaseEvent {

    private final Long userId;
    private final Long chatId;
    private final String username;
    private final String firstName;
    private final String originalFilename;
    private final String contentType;
    private final String bucket;
    private final String s3Key;
    private final Long fileSize;
    private final Instant uploadedAt;

    @JsonCreator
    public FileUploadedEvent(
            @JsonProperty("user_id") Long userId,
            @JsonProperty("chat_id") Long chatId,
            @JsonProperty("username") String username,
            @JsonProperty("first_name") String firstName,
            @JsonProperty("original_filename") String originalFilename,
            @JsonProperty("content_type") String contentType,
            @JsonProperty("minio_bucket") String bucket,
            @JsonProperty("minio_key") String s3Key,
            @JsonProperty("file_size") Long fileSize,
            @JsonProperty("uploaded_at") Instant uploadedAt
    ) {
        this.userId = userId;
        this.chatId = chatId;
        this.username = username;
        this.firstName = firstName;
        this.originalFilename = originalFilename;
        this.contentType = contentType;
        this.bucket = bucket;
        this.s3Key = s3Key;
        this.fileSize = fileSize;
        this.uploadedAt = uploadedAt;
    }
}
