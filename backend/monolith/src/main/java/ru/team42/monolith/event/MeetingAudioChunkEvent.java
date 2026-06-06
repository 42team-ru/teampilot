package ru.team42.monolith.event;

import lombok.Builder;
import lombok.Getter;
import lombok.extern.jackson.Jacksonized;
import ru.team42.backend.kafka_common.event.BaseEvent;

import java.time.Instant;
import java.util.List;

@Getter
@Builder
@Jacksonized
public class MeetingAudioChunkEvent extends BaseEvent {

    private final String meetingId;
    private final String teamId;
    private final Long recorderTelegramId;
    private final Integer chunkIndex;
    private final Boolean finalChunk;
    private final String bucket;
    private final String s3Key;
    private final String originalFilename;
    private final String contentType;
    private final Long sizeBytes;
    private final Instant recordedAt;

    @Builder.Default
    private final List<AudioNewEvent.TeamMemberDto> team = List.of();
    @Builder.Default
    private final List<AudioNewEvent.ColumnDto> columns = List.of();
    @Builder.Default
    private final List<AudioNewEvent.StickerDto> stickers = List.of();
}
