package ru.team42.monolith.consumer;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.event.ChatMessageEvent;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.service.ChatMessageService;

@Slf4j
@Component
@RequiredArgsConstructor
public class ChatMessageConsumer {

    private static final ObjectMapper MAPPER = new ObjectMapper()
            .findAndRegisterModules()
            .setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);

    private final ChatMessageService chatMessageService;

    @KafkaListener(topics = KafkaTopics.MESSAGES_RAW)
    public void consume(String json) throws Exception {
        ChatMessageEvent message = MAPPER.readValue(json, ChatMessageEvent.class);
        log.info("Received message from chat: {}", message.getChatId());
        chatMessageService.save(message);
    }
}
