package ru.team42.monolith.consumer;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import ru.team42.monolith.event.FileUploadedEvent;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.service.FileUploadService;

@Slf4j
@Component
@RequiredArgsConstructor
public class FileUploadConsumer {

    private final FileUploadService fileUploadService;

    @KafkaListener(topics = KafkaTopics.FILES_UPLOADED)
    public void consume(FileUploadedEvent event) {
        log.info("Received uploaded file from chat {}: {}", event.getChatId(), event.getS3Key());
        fileUploadService.save(event);
    }
}
