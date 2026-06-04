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
public class MessageBatchEvent extends BaseEvent {

    private final Long chatId;
    private final List<MessageDto> messages;
    private final Instant batchStart;
    private final Instant batchEnd;
    private final List<TeamMemberDto> team;
    private final List<ColumnDto> columns;

    @Getter
    @Builder
    @Jacksonized
    public static class MessageDto {
        private final Long userId;
        private final String username;
        private final String fullName;
        private final String text;
        private final Instant timestamp;
    }

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
}
