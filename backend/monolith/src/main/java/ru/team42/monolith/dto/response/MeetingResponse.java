package ru.team42.monolith.dto.response;

import ru.team42.monolith.entity.Meeting;

import java.time.LocalDateTime;
import java.util.UUID;

public record MeetingResponse(
        UUID id,
        UUID teamId,
        String meetingUrl,
        Long primaryRecorderTelegramId,
        boolean active,
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
                meeting.getCreatedAt()
        );
    }
}
