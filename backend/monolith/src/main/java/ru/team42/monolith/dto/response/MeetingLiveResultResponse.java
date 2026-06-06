package ru.team42.monolith.dto.response;

import ru.team42.monolith.event.MeetingLiveResultEvent;

import java.util.List;
import java.util.UUID;

public record MeetingLiveResultResponse(
        UUID meetingId,
        String teamId,
        Integer chunkIndex,
        String transcript,
        String summary,
        String context,
        List<TaskDto> tasks,
        List<StatusDto> statuses
) {
    public static MeetingLiveResultResponse from(MeetingLiveResultEvent event) {
        return new MeetingLiveResultResponse(
                UUID.fromString(event.getMeetingId()),
                event.getTeamId(),
                event.getChunkIndex(),
                event.getTranscript(),
                event.getSummary(),
                event.getContext(),
                event.getTasks().stream().map(TaskDto::from).toList(),
                event.getStatuses().stream().map(StatusDto::from).toList()
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
}
