package ru.team42.monolith.consumer;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.event.LlmTaskCreateEvent;
import ru.team42.monolith.service.TaskService;

@Slf4j
@Component
@RequiredArgsConstructor
public class LlmTaskCreateConsumer {

    private static final ObjectMapper MAPPER = new ObjectMapper()
            .findAndRegisterModules()
            .setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);

    private final TaskService taskService;

    @KafkaListener(topics = KafkaTopics.LLM_TASKS_CREATE)
    public void consume(String json) {
        LlmTaskCreateEvent event;
        try {
            event = MAPPER.readValue(json, LlmTaskCreateEvent.class);
        } catch (Exception e) {
            log.error("Failed to deserialize LlmTaskCreateEvent: {}", e.getMessage());
            return;
        }

        log.info("Received llm.tasks.create for chatId={} title='{}'",
                event.getChatId(), event.getTitle());

        try {
            taskService.createFromLlmEvent(event);
        } catch (Exception e) {
            log.error("Failed to process LlmTaskCreateEvent for chatId={}: {}",
                    event.getChatId(), e.getMessage());
        }
    }
}
