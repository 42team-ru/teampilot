package ru.team42.monolith.kafka.consumer;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.event.FileSummaryEvent;
import ru.team42.monolith.service.FileUploadService;

@Slf4j
@Component
@RequiredArgsConstructor
public class FileSummaryConsumer {

    private final FileUploadService fileUploadService;

    @KafkaListener(topics = KafkaTopics.FILES_TRANSCRIPT_READY)
    public void consume(FileSummaryEvent event) {
        log.info("Received file summary for fileId={} title={}", event.getFileId(), event.getTitle());
        try {
            fileUploadService.updateSummary(
                    event.getFileId(),
                    event.getTitle(),
                    event.getDescription(),
                    event.getSummary()
            );
        } catch (Exception e) {
            log.error("Failed to update summary for fileId={}: {}", event.getFileId(), e.getMessage(), e);
        }
    }
}
