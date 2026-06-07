package ru.team42.monolith.dto.response;

import ru.team42.monolith.event.MeetingLiveResultEvent;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record MeetingLiveResultResponse(
        UUID meetingId,
        String teamId,
        Integer chunkIndex,
        String transcript,
        String summary,
        String context,
        boolean finalResult,
        String title,
        String description,
        String recordingBucket,
        String recordingS3Key,
        String recordingContentType,
        Long recordingSizeBytes,
        String transcriptBucket,
        String transcriptS3Key,
        Instant finalizedAt,
        List<TaskDto> tasks,
        List<StatusDto> statuses,
        List<String> hints,
        List<SpeakerSegmentDto> speakerSegments
) {
    public static MeetingLiveResultResponse from(MeetingLiveResultEvent event) {
        return new MeetingLiveResultResponse(
                UUID.fromString(event.getMeetingId()),
                event.getTeamId(),
                event.getChunkIndex(),
                event.getTranscript(),
                event.getSummary(),
                event.getContext(),
                event.isFinalResult(),
                event.getTitle(),
                event.getDescription(),
                event.getRecordingBucket(),
                event.getRecordingS3Key(),
                event.getRecordingContentType(),
                event.getRecordingSizeBytes(),
                event.getTranscriptBucket(),
                event.getTranscriptS3Key(),
                event.getFinalizedAt(),
                event.getTasks() == null ? List.of() : event.getTasks().stream().map(TaskDto::from).toList(),
                event.getStatuses() == null ? List.of() : event.getStatuses().stream().map(StatusDto::from).toList(),
                event.getHints() == null ? List.of() : event.getHints(),
                event.getSpeakerSegments() == null ? List.of() : event.getSpeakerSegments().stream().map(SpeakerSegmentDto::from).toList()
        );
    }

    public record TaskDto(
            String title,
            String description,
            Long assigneeId,
            String deadline,
            String columnId,
            float confidence
    ) {
        static TaskDto from(MeetingLiveResultEvent.TaskDto task) {
            return new TaskDto(
                    task.getTitle(),
                    task.getDescription(),
                    task.getAssigneeId(),
                    task.getDeadline(),
                    task.getColumnId(),
                    task.getConfidence()
            );
        }
    }

    public record StatusDto(
            String taskId,
            Long assigneeId,
            String columnId,
            String action
    ) {
        static StatusDto from(MeetingLiveResultEvent.StatusDto status) {
            return new StatusDto(
                    status.getTaskId(),
                    status.getAssigneeId(),
                    status.getColumnId(),
                    status.getAction()
            );
        }
    }

    public record SpeakerSegmentDto(
            String speakerLabel,
            String sample
    ) {
        static SpeakerSegmentDto from(MeetingLiveResultEvent.SpeakerSegmentDto speaker) {
            return new SpeakerSegmentDto(
                    speaker.getSpeakerLabel(),
                    speaker.getSample()
            );
        }
    }
}
