package ru.team42.monolith.kafka.consumer;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.monolith.event.FileUploadedEvent;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.kafka.publisher.AudioEventPublisher;
import ru.team42.monolith.service.FileUploadService;

@Slf4j
@Component
@RequiredArgsConstructor
public class FileUploadConsumer {

    private final FileUploadService fileUploadService;
    private final AudioEventPublisher audioEventPublisher;

    @KafkaListener(topics = KafkaTopics.FILES_UPLOADED)
    @Transactional
    public void consume(FileUploadedEvent event) {
        log.info("Received uploaded file from chat {}: {}", event.getChatId(), event.getS3Key());
        var saved = fileUploadService.save(event);

        if (isAudioOrVideo(event.getContentType())) {
            audioEventPublisher.publishAudioNew(saved);
            log.info("Published audio.new for fileId={} contentType={}", saved.getId(), event.getContentType());
        }
    }

    private boolean isAudioOrVideo(String contentType) {
        return contentType != null
                && (contentType.startsWith("audio/") || contentType.startsWith("video/"));
    }
}
