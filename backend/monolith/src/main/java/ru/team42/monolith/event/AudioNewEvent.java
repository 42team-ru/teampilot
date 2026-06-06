package ru.team42.monolith.event;

import lombok.Builder;
import lombok.Getter;
import lombok.extern.jackson.Jacksonized;
import ru.team42.backend.kafka_common.event.BaseEvent;

import java.time.Instant;
import java.util.UUID;

@Getter
@Builder
@Jacksonized
public class AudioNewEvent extends BaseEvent {

    private final UUID fileId;
    private final String bucket;
    private final String s3Key;
    private final String originalFilename;
    private final String contentType;
    private final Long sizeBytes;
    private final Instant uploadedAt;
}
