package ru.team42.monolith.websocket;

import lombok.RequiredArgsConstructor;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.simp.stomp.StompCommand;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;
import org.springframework.messaging.support.ChannelInterceptor;
import org.springframework.messaging.support.MessageHeaderAccessor;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.stereotype.Component;
import ru.team42.monolith.repository.UserRepository;
import ru.team42.monolith.security.JwtService;
import ru.team42.monolith.security.TelegramAuthFilter;

import java.util.List;
import java.util.UUID;

@Component
@RequiredArgsConstructor
public class WebSocketAuthChannelInterceptor implements ChannelInterceptor {

    private static final String BEARER_PREFIX = "Bearer ";

    private final UserRepository userRepository;
    private final JwtService jwtService;

    @Override
    public Message<?> preSend(Message<?> message, MessageChannel channel) {
        StompHeaderAccessor accessor = MessageHeaderAccessor.getAccessor(message, StompHeaderAccessor.class);
        if (accessor != null && StompCommand.CONNECT.equals(accessor.getCommand())) {
            accessor.setUser(authenticate(accessor));
        }
        return message;
    }

    private UsernamePasswordAuthenticationToken authenticate(StompHeaderAccessor accessor) {
        var jwtAuthentication = authenticateWithJwt(accessor.getFirstNativeHeader("Authorization"));
        if (jwtAuthentication != null) {
            return jwtAuthentication;
        }

        var telegramAuthentication = authenticateWithTelegramId(
                accessor.getFirstNativeHeader(TelegramAuthFilter.HEADER)
        );
        if (telegramAuthentication != null) {
            return telegramAuthentication;
        }

        throw new AccessDeniedException("WebSocket authentication required");
    }

    private UsernamePasswordAuthenticationToken authenticateWithJwt(String authHeader) {
        if (authHeader == null || !authHeader.startsWith(BEARER_PREFIX)) {
            return null;
        }
        String token = authHeader.substring(BEARER_PREFIX.length());
        return jwtService.validateToken(token)
                .flatMap(claims -> {
                    try {
                        return userRepository.findById(UUID.fromString(claims.getSubject()));
                    } catch (IllegalArgumentException e) {
                        return java.util.Optional.empty();
                    }
                })
                .map(this::toAuthentication)
                .orElse(null);
    }

    private UsernamePasswordAuthenticationToken authenticateWithTelegramId(String header) {
        if (header == null || header.isBlank()) {
            return null;
        }
        try {
            return userRepository.findByTelegramId(Long.parseLong(header))
                    .map(this::toAuthentication)
                    .orElse(null);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private UsernamePasswordAuthenticationToken toAuthentication(ru.team42.monolith.entity.User user) {
        var authority = new SimpleGrantedAuthority("ROLE_" + user.getSystemRole().name());
        return new UsernamePasswordAuthenticationToken(user, null, List.of(authority));
    }
}
