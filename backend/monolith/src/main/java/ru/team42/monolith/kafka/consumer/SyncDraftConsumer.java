package ru.team42.monolith.kafka.consumer;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.event.SyncDraftEvent;
import ru.team42.monolith.service.EveningSyncService;

@Slf4j
@Component
@RequiredArgsConstructor
public class SyncDraftConsumer {

    private final EveningSyncService eveningSyncService;

    @KafkaListener(topics = KafkaTopics.SYNC_DRAFT)
    public void consume(SyncDraftEvent event) {
        log.info("Received sync.draft requestId={} user={}", event.getRequestId(), event.getTelegramUserId());
        try {
            eveningSyncService.handleDraft(event);
        } catch (Exception e) {
            log.error("Failed to process sync draft requestId={}: {}", event.getRequestId(), e.getMessage());
        }
    }
}
