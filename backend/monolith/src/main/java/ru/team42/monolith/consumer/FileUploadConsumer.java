package ru.team42.monolith.consumer;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.event.FileUploadedEvent;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.service.FileUploadService;

@Slf4j
@Component
@RequiredArgsConstructor
public class FileUploadConsumer {

    private static final ObjectMapper MAPPER = new ObjectMapper()
            .findAndRegisterModules()
            .setPropertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE);

    private final FileUploadService fileUploadService;

    @KafkaListener(topics = KafkaTopics.FILES_UPLOADED)
    public void consume(String json) throws Exception {
        FileUploadedEvent event = MAPPER.readValue(json, FileUploadedEvent.class);
        log.info("Received uploaded file from chat {}: {}", event.getChatId(), event.getS3Key());
        fileUploadService.save(event);
    }
}
