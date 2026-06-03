package ru.team42.monolith.consumer;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.backend.kafka_common.event.LlmStatusChangeEvent;
import ru.team42.monolith.entity.TaskStatus;
import ru.team42.monolith.service.TaskService;

@Slf4j
@Component
@RequiredArgsConstructor
public class LlmStatusChangeConsumer {

    private final TaskService taskService;

    @KafkaListener(topics = KafkaTopics.LLM_STATUS_CHANGE)
    public void consume(LlmStatusChangeEvent event, Acknowledgment ack) {
        log.info("LLM requests status change for task {}: '{}'", event.getTaskId(), event.getNewStatus());
        try {
            // Try to parse as internal enum first; otherwise treat as external status string
            TaskStatus internalStatus = tryParseInternal(event.getNewStatus());
            if (internalStatus != null) {
                taskService.syncStatusFromExternal(event.getTaskId(), event.getNewStatus());
            } else {
                taskService.syncStatusFromExternal(event.getTaskId(), event.getNewStatus());
            }
        } catch (Exception e) {
            log.error("Failed to update status for task {} from LLM event {}: {}",
                    event.getTaskId(), event.getEventId(), e.getMessage(), e);
        }
        ack.acknowledge();
    }

    private TaskStatus tryParseInternal(String value) {
        try {
            return TaskStatus.valueOf(value);
        } catch (IllegalArgumentException e) {
            return null;
        }
    }
}
