package ru.team42.backend.kafka_common.event;

import lombok.Builder;
import lombok.Getter;
import lombok.extern.jackson.Jacksonized;

import java.time.Instant;

@Getter
@Builder
public class ChatMessageEvent extends BaseEvent {

    private final Long messageId;
    private final Long chatId;
    private final Long userId;
    private final String username;
    private final String fullName;
    private final String text;
    private final Instant timestamp;
}
