package ru.team42.backend.room_common.model;

import lombok.AllArgsConstructor;
import lombok.Data;

/** Конверт исходящего сообщения: {"event": "PLAYER_JOINED", "payload": {...}} */
@Data
@AllArgsConstructor
public class OutboundEnvelope {
    private String event;
    private Object payload;
}
