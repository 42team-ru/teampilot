package ru.team42.monolith.dto.response;

import java.time.LocalDateTime;
import java.util.UUID;

public record UploadedFileResponse(
        UUID id,
        String originalFilename,
        String title,
        String description,
        String summary,
        String contentType,
        Long sizeBytes,
        LocalDateTime createdAt,
        String downloadUrl
) {}
