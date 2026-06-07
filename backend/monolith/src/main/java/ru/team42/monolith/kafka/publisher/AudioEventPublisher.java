package ru.team42.monolith.kafka.publisher;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.AbstractEventPublisher;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.entity.UploadedFile;
import ru.team42.monolith.event.AudioNewEvent;
import ru.team42.monolith.service.TeamKafkaContextFactory;

import java.time.Instant;
import java.util.UUID;

@Component
@RequiredArgsConstructor
public class AudioEventPublisher extends AbstractEventPublisher {

    private final TeamKafkaContextFactory teamKafkaContextFactory;

    public void publishAudioNew(UploadedFile file) {
        var teamUser = file.getTeamUser();
        var team = teamUser != null ? teamUser.getTeam() : null;
        UUID teamId = team != null ? team.getId() : null;

        var context = teamId != null ? teamKafkaContextFactory.build(teamId) : null;

        var event = AudioNewEvent.builder()
                .fileId(file.getId())
                .teamId(teamId != null ? teamId.toString() : null)
                .teamChatId(team != null ? team.getTelegramChatId() : null)
                .bucket(file.getBucket())
                .s3Key(file.getS3Key())
                .originalFilename(file.getOriginalFilename())
                .contentType(file.getContentType())
                .sizeBytes(file.getSizeBytes())
                .uploadedAt(Instant.now())
                .team(context != null ? context.team() : java.util.List.of())
                .columns(context != null ? context.columns() : java.util.List.of())
                .stickers(context != null ? context.stickers() : java.util.List.of())
                .build();

        send(KafkaTopics.AUDIO_NEW, file.getId().toString(), event);
    }
}
