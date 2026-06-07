package ru.team42.monolith.event;

import lombok.Builder;
import lombok.Getter;
import lombok.extern.jackson.Jacksonized;
import ru.team42.backend.kafka_common.event.BaseEvent;

import java.util.List;

@Getter
@Builder
@Jacksonized
public class SyncRequestEvent extends BaseEvent {

    private final String requestId;
    private final String teamId;
    private final Long chatId;
    private final Long telegramUserId;
    private final String username;
    private final String rawText;
    private final List<TaskSummary> activeTasks;

    @Getter
    @Builder
    @Jacksonized
    public static class TaskSummary {
        private final String id;
        private final String title;
        private final String description;
    }
}
