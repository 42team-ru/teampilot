package ru.team42.backend.room_common.config;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.ChannelRegistration;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;
import ru.team42.backend.room_common.interceptor.RoomChannelInterceptor;

/**
 * Используется, когда приложение владеет конфигурацией WebSocket (room.auto-configure-websocket=false).
 * Внедряет только перехватчик канала; остальное зависит от приложения.
 */
@Configuration(proxyBeanMethods = false)
@ConditionalOnProperty(name = "room.auto-configure-websocket", havingValue = "false")
public class RoomChannelOnlyConfig implements WebSocketMessageBrokerConfigurer {

    private final RoomChannelInterceptor channelInterceptor;

    public RoomChannelOnlyConfig(RoomChannelInterceptor channelInterceptor) {
        this.channelInterceptor = channelInterceptor;
    }

    @Override
    public void configureClientInboundChannel(ChannelRegistration registration) {
        registration.interceptors(channelInterceptor);
    }
}
