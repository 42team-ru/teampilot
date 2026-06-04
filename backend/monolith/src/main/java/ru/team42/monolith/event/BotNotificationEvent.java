package ru.team42.monolith.event;

import lombok.Getter;
import ru.team42.backend.kafka_common.event.BaseEvent;

import java.util.UUID;

@Getter
public class BotNotificationEvent extends BaseEvent {

    public static final String TYPE_DEADLINE = "DEADLINE";
    public static final String TYPE_STALE = "STALE";

    private final Long telegramId;
    private final Long chatId;
    private final String type;
    private final UUID taskId;
    private final String taskTitle;

    public BotNotificationEvent(Long telegramId, Long chatId, String type, UUID taskId, String taskTitle) {
        this.telegramId = telegramId;
        this.chatId = chatId;
        this.type = type;
        this.taskId = taskId;
        this.taskTitle = taskTitle;
    }
}
