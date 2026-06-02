package ru.team42.backend.room_common.example.presence;

import lombok.Data;

import java.time.Instant;

@Data
public class PresenceInfo {

    public enum Status { ONLINE, IDLE, AWAY }

    private final String participantId;
    private String displayName;
    private Status status = Status.ONLINE;
    /** Позиция курсора (для collaborative-инструментов). */
    private Double cursorX;
    private Double cursorY;
    private Instant lastSeenAt = Instant.now();
}
