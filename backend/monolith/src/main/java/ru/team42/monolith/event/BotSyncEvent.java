package ru.team42.monolith.event;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Builder;
import lombok.Getter;
import lombok.extern.jackson.Jacksonized;
import ru.team42.backend.kafka_common.event.BaseEvent;

import java.util.List;

@Getter
@Builder
@Jacksonized
public class BotSyncEvent extends BaseEvent {

    public static final String TYPE_SYNC_PROMPT  = "SYNC_PROMPT";
    public static final String TYPE_SYNC_DRAFT   = "SYNC_DRAFT";
    public static final String TYPE_SYNC_SUMMARY = "SYNC_SUMMARY";

    private final String type;

    /** Для TYPE_SYNC_PROMPT — ID группового чата */
    private final Long chatId;

    /** Для TYPE_SYNC_DRAFT — одному пользователю */
    private final Long recipientTelegramId;

    /** Для TYPE_SYNC_SUMMARY — всем менеджерам */
    private final List<Long> recipientTelegramIds;

    /** Заполняется для TYPE_SYNC_DRAFT */
    private final List<DraftItem> draft;

    /** Заполняется для TYPE_SYNC_SUMMARY */
    private final SyncSummary summary;

    @Getter
    @Builder
    @Jacksonized
    public static class DraftItem {
        private final int index;
        private final String userText;
        private final String taskId;
        private final String taskTitle;
        @JsonProperty("isNewTask")
        private final boolean isNewTask;
        private final Long assigneeTelegramId;
        private final String assigneeName;
    }

    @Getter
    @Builder
    @Jacksonized
    public static class SyncSummary {
        private final List<String> respondedUsernames;
        private final List<String> notRespondedUsernames;
        private final int tasksCompleted;
        private final int newTasksPendingApproval;
        /** List of "Name — reason" strings for users who submitted /excuse */
        private final List<String> excusedEntries;
    }
}
