package ru.team42.backend.room_common.example.presence.dto;

import lombok.Data;
import ru.team42.backend.room_common.example.presence.PresenceInfo;

@Data
public class UpdatePresenceDto {
    private String displayName;
    private PresenceInfo.Status status;
    private Double cursorX;
    private Double cursorY;
}
