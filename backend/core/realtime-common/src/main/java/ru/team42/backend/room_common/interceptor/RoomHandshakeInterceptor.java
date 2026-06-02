package ru.team42.backend.room_common.interceptor;

import lombok.extern.slf4j.Slf4j;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.security.authentication.AnonymousAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.server.HandshakeInterceptor;

import java.util.Map;
import java.util.UUID;
import java.util.function.Function;

/**
 * Заполняет атрибуты сессии во время установления соединения WebSocket:
 * - {@code participantId} — новый UUID для каждого соединения
 * - {@code userId} — извлекается из контекста безопасности (допускается значение null)
 *
 * Переопределите {@link #defaultUserIdExtractor()} или предоставьте пользовательский
 * {@code Function<Authentication, Long>} bean для настройки извлечения userId.
 */
@Slf4j
public class RoomHandshakeInterceptor implements HandshakeInterceptor {

    static final String PARTICIPANT_ID = "participantId";
    static final String USER_ID = "userId";

    private final Function<Authentication, Long> userIdExtractor;

    public RoomHandshakeInterceptor() {
        this(defaultUserIdExtractor());
    }

    public RoomHandshakeInterceptor(Function<Authentication, Long> userIdExtractor) {
        this.userIdExtractor = userIdExtractor;
    }

    @Override
    public boolean beforeHandshake(ServerHttpRequest request,
                                   ServerHttpResponse response,
                                   WebSocketHandler wsHandler,
                                   Map<String, Object> attributes) {
        attributes.put(PARTICIPANT_ID, UUID.randomUUID().toString());

        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.isAuthenticated() && !(auth instanceof AnonymousAuthenticationToken)) {
            try {
                Long userId = userIdExtractor.apply(auth);
                if (userId != null) {
                    attributes.put(USER_ID, userId);
                }
            } catch (Exception e) {
                log.warn("[room-common] failed to extract userId from authentication", e);
            }
        }
        return true;
    }

    @Override
    public void afterHandshake(ServerHttpRequest request, ServerHttpResponse response,
                               WebSocketHandler wsHandler, Exception exception) {}

    /**
     * Экстрактор по умолчанию — возвращает null. Переопределите его в своем приложении, предоставив
     * пользовательский bean-компонент {@code RoomHandshakeInterceptor}.
     */
    private static Function<Authentication, Long> defaultUserIdExtractor() {
        return auth -> null;
    }
}
