package ru.team42.backend.kafka_common.event;

import lombok.Builder;
import lombok.Getter;

import java.util.UUID;

@Getter
@Builder
public class TranscriptReadyEvent extends BaseEvent {

    private final UUID fileId;
    private final String bucket;
    private final String s3Key;
}
