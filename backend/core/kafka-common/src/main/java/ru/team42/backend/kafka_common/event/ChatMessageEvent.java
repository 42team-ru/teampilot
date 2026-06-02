package ru.team42.backend.kafka_common.event;

import lombok.Builder;
import lombok.Getter;
import lombok.extern.jackson.Jacksonized;

import java.time.Instant;

@Getter
@Builder
public class ChatMessageEvent extends BaseEvent {

    private final Long chatId;
    private final String tgUser;
    private final String text;
    private final Instant timestamp;
}
