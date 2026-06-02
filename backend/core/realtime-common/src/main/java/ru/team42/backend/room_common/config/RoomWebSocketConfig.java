package ru.team42.backend.room_common.config;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.ChannelRegistration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;
import ru.team42.backend.room_common.interceptor.RoomChannelInterceptor;
import ru.team42.backend.room_common.interceptor.RoomHandshakeInterceptor;

@Configuration(proxyBeanMethods = false)
@EnableWebSocketMessageBroker
@ConditionalOnProperty(name = "room.auto-configure-websocket", havingValue = "true", matchIfMissing = true)
public class RoomWebSocketConfig implements WebSocketMessageBrokerConfigurer {

    private final RoomHandshakeInterceptor handshakeInterceptor;
    private final RoomChannelInterceptor channelInterceptor;
    private final RoomProperties properties;

    public RoomWebSocketConfig(RoomHandshakeInterceptor handshakeInterceptor,
                                RoomChannelInterceptor channelInterceptor,
                                RoomProperties properties) {
        this.handshakeInterceptor = handshakeInterceptor;
        this.channelInterceptor = channelInterceptor;
        this.properties = properties;
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        registry.addEndpoint(properties.getWebsocketEndpoint())
                .addInterceptors(handshakeInterceptor)
                .setAllowedOriginPatterns("*")
                .withSockJS();
    }

    @Override
    public void configureMessageBroker(MessageBrokerRegistry config) {
        config.enableSimpleBroker(properties.getTopicPrefix(), "/queue");
        config.setApplicationDestinationPrefixes(properties.getAppPrefix());
        config.setUserDestinationPrefix("/user");
    }

    @Override
    public void configureClientInboundChannel(ChannelRegistration registration) {
        registration.interceptors(channelInterceptor);
    }
}
