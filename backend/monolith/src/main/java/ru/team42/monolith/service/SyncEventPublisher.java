package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.AbstractEventPublisher;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.event.BotSyncEvent;
import ru.team42.monolith.event.SyncDraftEvent;
import ru.team42.monolith.event.SyncRequestEvent;

import java.util.List;
import java.util.UUID;

@Slf4j
@Component
@RequiredArgsConstructor
public class SyncEventPublisher extends AbstractEventPublisher {

    public void publishSyncPrompt(Long chatId, List<Long> memberTelegramIds) {
        send(KafkaTopics.BOTS_NOTIFICATIONS, chatId.toString(),
                BotSyncEvent.builder()
                        .type(BotSyncEvent.TYPE_SYNC_PROMPT)
                        .chatId(chatId)
                        .recipientTelegramIds(memberTelegramIds)
                        .build());
        log.info("Evening sync prompt sent to chatId={} recipients={}", chatId, memberTelegramIds.size());
    }

    public void publishSyncRequest(SyncRequestEvent event) {
        send(KafkaTopics.SYNC_REQUESTS, event.getTeamId(), event);
        log.info("Sync request published requestId={} user={}", event.getRequestId(), event.getTelegramUserId());
    }

    public void publishDraftToUser(Long telegramUserId, Long chatId, List<SyncDraftEvent.DraftItem> items) {
        List<BotSyncEvent.DraftItem> botItems = items.stream()
                .map(i -> BotSyncEvent.DraftItem.builder()
                        .index(i.getIndex())
                        .userText(i.getUserText())
                        .taskId(i.getTaskId())
                        .taskTitle(i.getTaskTitle())
                        .isNewTask(i.isNewTask())
                        .assigneeTelegramId(i.getAssigneeTelegramId())
                        .assigneeName(i.getAssigneeName())
                        .build())
                .toList();

        send(KafkaTopics.BOTS_NOTIFICATIONS, telegramUserId.toString(),
                BotSyncEvent.builder()
                        .type(BotSyncEvent.TYPE_SYNC_DRAFT)
                        .chatId(chatId)
                        .recipientTelegramId(telegramUserId)
                        .draft(botItems)
                        .build());
        log.info("Sync draft sent to user={} chatId={}", telegramUserId, chatId);
    }

    public void publishSyncSummary(List<Long> managerTelegramIds, UUID teamId,
                                   List<String> responded, List<String> notResponded,
                                   int completed, int pending) {
        publishSyncSummary(managerTelegramIds, teamId, responded, notResponded, completed, pending, List.of());
    }

    public void publishSyncSummary(List<Long> managerTelegramIds, UUID teamId,
                                   List<String> responded, List<String> notResponded,
                                   int completed, int pending, List<String> excused) {
        send(KafkaTopics.BOTS_NOTIFICATIONS, teamId.toString(),
                BotSyncEvent.builder()
                        .type(BotSyncEvent.TYPE_SYNC_SUMMARY)
                        .recipientTelegramIds(managerTelegramIds)
                        .summary(BotSyncEvent.SyncSummary.builder()
                                .respondedUsernames(responded)
                                .notRespondedUsernames(notResponded)
                                .tasksCompleted(completed)
                                .newTasksPendingApproval(pending)
                                .excusedEntries(excused)
                                .build())
                        .build());
        log.info("Sync summary sent to {} manager(s) for team={}", managerTelegramIds.size(), teamId);
    }
}
