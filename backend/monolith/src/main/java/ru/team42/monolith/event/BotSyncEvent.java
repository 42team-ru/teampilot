package ru.team42.monolith.event;

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
    public static final String TYPE_SYNC_SUMMARY = "SYNC_SUMMARY";

    private final String type;

    /** Для TYPE_SYNC_PROMPT — ID группового чата */
    private final Long chatId;

    /** Для TYPE_SYNC_SUMMARY — ID команды */
    private final String teamId;

    /** Для TYPE_SYNC_SUMMARY — всем менеджерам */
    private final List<Long> recipientTelegramIds;

    /** Заполняется для TYPE_SYNC_SUMMARY */
    private final SyncSummary summary;

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
        /** Per-member sync details, one entry per team member */
        private final List<MemberSummary> members;

        @Getter
        @Builder
        @Jacksonized
        public static class MemberSummary {
            private final Long telegramId;
            private final String username;
            private final String status;
            private final String excuseReason;
            private final List<String> confirmedTasks;
            private final List<String> pendingTasks;
            private final String rawText;
        }
    }
}
