package ru.team42.monolith.dto.response;

import ru.team42.monolith.entity.Meeting;

import java.time.Instant;
import java.time.LocalDateTime;
import java.util.UUID;

public record MeetingResponse(
        UUID id,
        UUID teamId,
        String meetingUrl,
        Long primaryRecorderTelegramId,
        boolean active,
        String recordingBucket,
        String recordingS3Key,
        String recordingContentType,
        Long recordingSizeBytes,
        String transcriptBucket,
        String transcriptS3Key,
        String title,
        String description,
        String summary,
        Instant finalizedAt,
        LocalDateTime createdAt
) {
    public static MeetingResponse from(Meeting meeting) {
        var primaryRecorder = meeting.getPrimaryRecorder();
        var primaryUser = primaryRecorder != null ? primaryRecorder.getUser() : null;
        return new MeetingResponse(
                meeting.getId(),
                meeting.getTeam().getId(),
                meeting.getMeetingUrl(),
                primaryUser != null ? primaryUser.getTelegramId() : null,
                meeting.isActive(),
                meeting.getRecordingBucket(),
                meeting.getRecordingS3Key(),
                meeting.getRecordingContentType(),
                meeting.getRecordingSizeBytes(),
                meeting.getTranscriptBucket(),
                meeting.getTranscriptS3Key(),
                meeting.getTitle(),
                meeting.getDescription(),
                meeting.getSummary(),
                meeting.getFinalizedAt(),
                meeting.getCreatedAt()
        );
    }
}
