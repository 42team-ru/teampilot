package ru.team42.backend.room_common.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.Data;

/** Входящий STOMP-конверт сообщения: {"event": "JOIN", "payload": {...}} */
@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class RoomEnvelope {
    private String event;
    private JsonNode payload;
}
