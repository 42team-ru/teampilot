package ru.team42.monolith.event;

import lombok.Builder;
import lombok.Getter;
import lombok.extern.jackson.Jacksonized;
import ru.team42.backend.kafka_common.event.BaseEvent;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Getter
@Builder
@Jacksonized
public class AudioNewEvent extends BaseEvent {

    private final UUID fileId;
    private final String teamId;
    private final Long teamChatId;
    private final String bucket;
    private final String s3Key;
    private final String originalFilename;
    private final String contentType;
    private final Long sizeBytes;
    private final Instant uploadedAt;

    @Builder.Default
    private final List<TeamMemberDto> team = List.of();
    @Builder.Default
    private final List<ColumnDto> columns = List.of();
    @Builder.Default
    private final List<StickerDto> stickers = List.of();

    @Getter
    @Builder
    @Jacksonized
    public static class TeamMemberDto {
        private final Long telegramId;
        private final String username;
        private final String fullName;
        private final String role;
        private final String position;
    }

    @Getter
    @Builder
    @Jacksonized
    public static class ColumnDto {
        private final String id;
        private final String title;
    }

    @Getter
    @Builder
    @Jacksonized
    public static class StickerStateDto {
        private final String id;
        private final String title;
    }

    @Getter
    @Builder
    @Jacksonized
    public static class StickerDto {
        private final String id;
        private final String title;
        private final String type;
        @Builder.Default
        private final List<StickerStateDto> states = List.of();
    }
}
