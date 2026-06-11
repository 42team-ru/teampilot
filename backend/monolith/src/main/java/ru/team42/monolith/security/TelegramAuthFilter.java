package ru.team42.monolith.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import ru.team42.monolith.config.AppProperties;
import ru.team42.monolith.repository.UserRepository;

import java.io.IOException;
import java.util.List;
import java.util.UUID;

import static ru.team42.monolith.security.RestSecurityErrorHandler.AUTH_FAILURE_DETAIL_ATTRIBUTE;

@Component
@RequiredArgsConstructor
public class TelegramAuthFilter extends OncePerRequestFilter {

    public static final String HEADER = "X-Telegram-Id";
    public static final String BOT_SECRET_HEADER = "X-Bot-Secret";
    private static final String BEARER_PREFIX = "Bearer ";

    private final UserRepository userRepository;
    private final AppProperties appProperties;
    private final JwtService jwtService;
    private final TelegramInitDataVerifier initDataVerifier;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        if (tryAuthenticateWithJwt(request)) {
            chain.doFilter(request, response);
            return;
        }

        boolean authenticated = tryAuthenticateWithInitData(request);
        if (!authenticated) {
            authenticated = tryAuthenticateWithTelegramId(request);
        }
        if (!authenticated) {
            tryAuthenticateAsBot(request);
        }

        chain.doFilter(request, response);
    }

    private boolean tryAuthenticateWithJwt(HttpServletRequest request) {
        String authHeader = request.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith(BEARER_PREFIX)) {
            return false;
        }

        String token = authHeader.substring(BEARER_PREFIX.length());
        return jwtService.validateToken(token).map(claims -> {
            try {
                UUID userId = UUID.fromString(claims.getSubject());
                return userRepository.findById(userId).map(user -> {
                    var authority = new SimpleGrantedAuthority("ROLE_" + user.getSystemRole().name());
                    var auth = new UsernamePasswordAuthenticationToken(user, null, List.of(authority));
                    SecurityContextHolder.getContext().setAuthentication(auth);
                    return true;
                }).orElse(false);
            } catch (IllegalArgumentException e) {
                return false;
            }
        }).orElse(false);
    }

    private boolean tryAuthenticateWithInitData(HttpServletRequest request) {
        String initData = request.getHeader(TelegramInitDataVerifier.INIT_DATA_HEADER);
        if (initData == null || initData.isBlank()) return false;

        if (!initDataVerifier.verify(initData)) {
            request.setAttribute(AUTH_FAILURE_DETAIL_ATTRIBUTE, "Invalid X-Telegram-Init-Data signature");
            return false;
        }

        return initDataVerifier.extractUserInfo(initData).flatMap(info ->
                userRepository.findByTelegramId(info.id()).map(user -> {
                    var authority = new SimpleGrantedAuthority("ROLE_" + user.getSystemRole().name());
                    var auth = new UsernamePasswordAuthenticationToken(user, null, List.of(authority));
                    SecurityContextHolder.getContext().setAuthentication(auth);
                    return true;
                })
        ).orElseGet(() -> {
            request.setAttribute(AUTH_FAILURE_DETAIL_ATTRIBUTE,
                    "User from Mini App initData not found — use /auth/telegram/mini-app to login first");
            return false;
        });
    }

    private boolean tryAuthenticateWithTelegramId(HttpServletRequest request) {
        String header = request.getHeader(HEADER);
        if (header == null || header.isBlank()) {
            return false;
        }

        try {
            long telegramId = Long.parseLong(header);
            var user = userRepository.findByTelegramId(telegramId);
            if (user.isPresent()) {
                var authority = new SimpleGrantedAuthority("ROLE_" + user.get().getSystemRole().name());
                var auth = new UsernamePasswordAuthenticationToken(user.get(), null, List.of(authority));
                SecurityContextHolder.getContext().setAuthentication(auth);
                return true;
            } else {
                request.setAttribute(
                        AUTH_FAILURE_DETAIL_ATTRIBUTE,
                        "User with Telegram ID %d not found".formatted(telegramId)
                );
                return false;
            }
        } catch (NumberFormatException e) {
            request.setAttribute(
                    AUTH_FAILURE_DETAIL_ATTRIBUTE,
                    "Invalid X-Telegram-Id header '%s': expected an integer".formatted(header)
            );
            return false;
        }
    }

    private void tryAuthenticateAsBot(HttpServletRequest request) {
        String botSecret = request.getHeader(BOT_SECRET_HEADER);
        if (botSecret != null && botSecret.equals(appProperties.getBot().getSecret())) {
            var authority = new SimpleGrantedAuthority("ROLE_BOT");
            var auth = new UsernamePasswordAuthenticationToken("bot", null, List.of(authority));
            SecurityContextHolder.getContext().setAuthentication(auth);
            request.removeAttribute(AUTH_FAILURE_DETAIL_ATTRIBUTE); // из v1: сброс ошибки при успехе бота
        } else if (botSecret != null) {
            request.setAttribute(AUTH_FAILURE_DETAIL_ATTRIBUTE, "Invalid X-Bot-Secret header");
        }
    }
}