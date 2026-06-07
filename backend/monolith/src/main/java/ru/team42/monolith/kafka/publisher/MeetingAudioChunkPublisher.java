package ru.team42.monolith.kafka.publisher;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.AbstractEventPublisher;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.event.MeetingAudioChunkEvent;
import ru.team42.monolith.entity.Meeting;
import ru.team42.monolith.service.TeamKafkaContextFactory;

import java.time.Instant;

@Component
@RequiredArgsConstructor
public class MeetingAudioChunkPublisher extends AbstractEventPublisher {

    private final TeamKafkaContextFactory teamKafkaContextFactory;

    public void publishChunk(
            Meeting meeting,
            int chunkIndex,
            boolean finalChunk,
            String bucket,
            String s3Key,
            String originalFilename,
            String contentType,
            long sizeBytes
    ) {
        var context = teamKafkaContextFactory.build(meeting.getTeam().getId());
        var recorderUser = meeting.getPrimaryRecorder().getUser();
        var event = MeetingAudioChunkEvent.builder()
                .meetingId(meeting.getId().toString())
                .teamId(meeting.getTeam().getId().toString())
                .recorderTelegramId(recorderUser != null ? recorderUser.getTelegramId() : null)
                .chunkIndex(chunkIndex)
                .finalChunk(finalChunk)
                .bucket(bucket)
                .s3Key(s3Key)
                .originalFilename(originalFilename)
                .contentType(contentType)
                .sizeBytes(sizeBytes)
                .recordedAt(Instant.now())
                .team(context.team())
                .columns(context.columns())
                .stickers(context.stickers())
                .build();

        send(KafkaTopics.MEETINGS_AUDIO_CHUNKS, event.getMeetingId(), event);
    }
}
