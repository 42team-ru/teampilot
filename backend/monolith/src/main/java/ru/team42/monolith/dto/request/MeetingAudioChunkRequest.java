package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

public record MeetingAudioChunkRequest(
        @NotNull @Min(0) Integer chunkIndex,
        @NotBlank String audioBase64,
        @Size(max = 255) String contentType,
        @Size(max = 512) String originalFilename,
        Boolean finalChunk
) {
}
