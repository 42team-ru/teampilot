package ru.team42.monolith.dto.response;

import java.util.UUID;

public record AudioUploadResponse(
        UUID fileId,
        String bucket,
        String s3Key,
        String originalFilename,
        Long sizeBytes
) {}
