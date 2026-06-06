package ru.team42.monolith.kafka.publisher;

import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.AbstractEventPublisher;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.backend.kafka_common.event.TranscriptReadyEvent;

import java.util.UUID;

@Component
public class TranscriptEventPublisher extends AbstractEventPublisher {

    public void publishTranscriptReady(UUID fileId, String teamId, String bucket, String s3Key) {
        var event = TranscriptReadyEvent.builder()
                .fileId(fileId)
                .teamId(teamId)
                .bucket(bucket)
                .s3Key(s3Key)
                .build();
        send(KafkaTopics.TRANSCRIPT_READY, fileId.toString(), event);
    }
}
