package ru.team42.backend.room_common.model;

import lombok.Builder;
import lombok.Data;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Представляет собой отдельное WebSocket-соединение в комнате.
 *
 * sessionId — сессия STOMP/WebSocket (в рамках соединения)
 * participantId — идентификатор в рамках комнаты (UUID, сохраняется при повторном подключении)
 * userId — глобальный аутентифицированный пользователь (может быть null для анонимных пользователей)
 */
@Data
@Builder
public class RoomSession {

    private final String sessionId;
    private final String participantId;
    private final Long userId;
    private final String roomType;
    private final String roomId;

    @Builder.Default
    private final Map<String, Object> attributes = new ConcurrentHashMap<>();
}
