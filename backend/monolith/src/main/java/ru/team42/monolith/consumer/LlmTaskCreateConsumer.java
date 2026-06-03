package ru.team42.monolith.consumer;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.backend.kafka_common.event.LlmTaskCreateEvent;
import ru.team42.monolith.service.TaskService;

@Slf4j
@Component
@RequiredArgsConstructor
public class LlmTaskCreateConsumer {

    private final TaskService taskService;

    @KafkaListener(topics = KafkaTopics.LLM_TASKS_CREATE)
    public void consume(LlmTaskCreateEvent event, Acknowledgment ack) {
        log.info("LLM detected task in chat {}: '{}'", event.getChatId(), event.getTitle());
        try {
            taskService.createFromLlm(
                    event.getTitle(),
                    event.getDescription(),
                    event.getChatId(),
                    event.getAssigneeUsername(),
                    event.getSourceContext()
            );
        } catch (Exception e) {
            log.error("Failed to create task from LLM event {}: {}", event.getEventId(), e.getMessage(), e);
        }
        ack.acknowledge();
    }
}
