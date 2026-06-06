package ru.team42.monolith.kafka.consumer;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.event.LlmStatusChangeEvent;
import ru.team42.monolith.service.TaskService;

@Slf4j
@Component
@RequiredArgsConstructor
public class LlmStatusChangeConsumer {

    private final TaskService taskService;

    @KafkaListener(topics = KafkaTopics.LLM_STATUS_CHANGE)
    public void consume(LlmStatusChangeEvent event) {
        log.info("Received llm.status.change action={} taskId={} teamId={}",
                event.getAction(), event.getTaskId(), event.getTeamId());
        try {
            taskService.handleStatusChange(event);
        } catch (Exception e) {
            log.error("Failed to process status change action={} taskId={}: {}",
                    event.getAction(), event.getTaskId(), e.getMessage());
        }
    }
}
