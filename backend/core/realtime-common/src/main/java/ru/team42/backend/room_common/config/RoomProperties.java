package ru.team42.backend.room_common.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Data
@ConfigurationProperties(prefix = "room")
public class RoomProperties {

    /** STOMP application destination prefix. Must match the broker config. */
    /** Префикс назначения приложения STOMP. Должен соответствовать конфигурации брокера. */
    private String appPrefix = "/app";

    /** STOMP topic prefix used for room broadcasts. */
    /** Префикс темы STOMP, используемый для трансляций в комнат. */
    private String topicPrefix = "/topic";

    /**
     * WebSocket endpoint path.
     * Only used when {@code room.auto-configure-websocket=true}.
     */
    /**
     * Путь к конечной точке WebSocket.
     * Используется только при {@code room.auto-configure-websocket=true}.
     */
    private String websocketEndpoint = "/ws";

    /**
     * When true the library registers the WebSocket endpoint, simple broker,
     * and destination prefixes automatically.
     * Set to false if you have your own {@code @EnableWebSocketMessageBroker} config.
     */
    /**
     * Если значение равно true, библиотека автоматически регистрирует конечную точку WebSocket, простой брокер и
     * префиксы назначения.
     * Установите значение false, если у вас есть собственная конфигурация {@code @EnableWebSocketMessageBroker}.
     */
    private boolean autoConfigureWebsocket = true;
}
