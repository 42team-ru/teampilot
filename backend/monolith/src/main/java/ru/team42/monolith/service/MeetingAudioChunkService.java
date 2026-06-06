package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.s3_common.config.S3Properties;
import ru.team42.backend.s3_common.service.S3Service;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.dto.request.MeetingAudioChunkRequest;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.kafka.publisher.MeetingAudioChunkPublisher;
import ru.team42.monolith.repository.TeamUserRepository;

import java.io.ByteArrayInputStream;
import java.util.Base64;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class MeetingAudioChunkService {

    private static final String DEFAULT_CONTENT_TYPE = "audio/webm";
    private static final String DEFAULT_BUCKET = "audio";

    private final MeetingService meetingService;
    private final TeamUserRepository teamUserRepository;
    private final S3Service s3Service;
    private final S3Properties s3Properties;
    private final MeetingAudioChunkPublisher meetingAudioChunkPublisher;

    @Transactional
    public void acceptChunk(UUID meetingId, MeetingAudioChunkRequest request, User sender) {
        if (sender == null || sender.getTelegramId() == null) {
            throw AppException.unauthorized("Telegram user authentication required for meeting audio stream");
        }

        var meeting = meetingService.getActiveMeeting(meetingId);
        var senderMembership = teamUserRepository.findByTeamIdAndUserTelegramId(
                meeting.getTeam().getId(),
                sender.getTelegramId()
        ).orElseThrow(() -> AppException.forbidden(
                "Access denied: Telegram user %d is not a member of meeting team %s"
                        .formatted(sender.getTelegramId(), meeting.getTeam().getId())
        ));

        if (!senderMembership.getId().equals(meeting.getPrimaryRecorder().getId())) {
            throw AppException.forbidden(
                    "Only primary recorder can publish audio chunks for meeting %s".formatted(meetingId)
            );
        }

        byte[] audioBytes = decodeAudio(request.audioBase64());
        if (audioBytes.length == 0) {
            throw AppException.badRequest("Audio chunk is empty");
        }

        String contentType = normalizeContentType(request.contentType());
        String originalFilename = normalizeFilename(request.originalFilename(), request.chunkIndex(), contentType);
        String bucket = s3Properties.getDefaultBucket() != null && !s3Properties.getDefaultBucket().isBlank()
                ? s3Properties.getDefaultBucket()
                : DEFAULT_BUCKET;
        String s3Key = buildS3Key(meetingId, request.chunkIndex(), originalFilename);

        s3Service.upload(bucket, s3Key, new ByteArrayInputStream(audioBytes), audioBytes.length, contentType);
        meetingAudioChunkPublisher.publishChunk(
                meeting,
                request.chunkIndex(),
                Boolean.TRUE.equals(request.finalChunk()),
                bucket,
                s3Key,
                originalFilename,
                contentType,
                audioBytes.length
        );
    }

    private byte[] decodeAudio(String audioBase64) {
        String payload = audioBase64;
        int commaIndex = payload.indexOf(',');
        if (payload.startsWith("data:") && commaIndex >= 0) {
            payload = payload.substring(commaIndex + 1);
        }
        try {
            return Base64.getDecoder().decode(payload);
        } catch (IllegalArgumentException e) {
            throw AppException.badRequest("audioBase64 must contain valid base64 data");
        }
    }

    private String normalizeContentType(String contentType) {
        return contentType != null && !contentType.isBlank() ? contentType : DEFAULT_CONTENT_TYPE;
    }

    private String normalizeFilename(String filename, int chunkIndex, String contentType) {
        if (filename != null && !filename.isBlank()) {
            return filename;
        }
        return "chunk-%06d.%s".formatted(chunkIndex, extensionFor(contentType));
    }

    private String buildS3Key(UUID meetingId, int chunkIndex, String originalFilename) {
        return "meetings/%s/chunks/%06d-%s".formatted(
                meetingId,
                chunkIndex,
                originalFilename.replaceAll("[^a-zA-Z0-9._-]", "_")
        );
    }

    private String extensionFor(String contentType) {
        return switch (contentType) {
            case "audio/ogg" -> "ogg";
            case "audio/mpeg" -> "mp3";
            case "audio/wav", "audio/x-wav" -> "wav";
            default -> "webm";
        };
    }
}
