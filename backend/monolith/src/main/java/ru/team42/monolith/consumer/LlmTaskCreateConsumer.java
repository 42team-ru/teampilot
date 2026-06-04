package ru.team42.monolith.consumer;

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

    private final TaskService taskService;

    @KafkaListener(topics = KafkaTopics.LLM_TASKS_CREATE)
    public void consume(LlmTaskCreateEvent event) {
        log.info("Received llm.tasks.create for chatId={} title='{}'",
                event.getChatId(), event.getTitle());
        taskService.createFromLlmEvent(event);
    }
}
