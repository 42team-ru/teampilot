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

@Component
@RequiredArgsConstructor
public class TelegramAuthFilter extends OncePerRequestFilter {

    public static final String HEADER = "X-Telegram-Id";
    public static final String BOT_SECRET_HEADER = "X-Bot-Secret";
    private static final String BEARER_PREFIX = "Bearer ";

    private final UserRepository userRepository;
    private final AppProperties appProperties;
    private final JwtService jwtService;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        if (tryAuthenticateWithJwt(request)) {
            chain.doFilter(request, response);
            return;
        }

        boolean authenticated = tryAuthenticateWithTelegramId(request);

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

    private boolean tryAuthenticateWithTelegramId(HttpServletRequest request) {
        String header = request.getHeader(HEADER);
        if (header == null) return false;
        try {
            long telegramId = Long.parseLong(header);
            userRepository.findByTelegramId(telegramId).ifPresent(user -> {
                var authority = new SimpleGrantedAuthority("ROLE_" + user.getSystemRole().name());
                var auth = new UsernamePasswordAuthenticationToken(user, null, List.of(authority));
                SecurityContextHolder.getContext().setAuthentication(auth);
            });
            return SecurityContextHolder.getContext().getAuthentication() != null;
        } catch (NumberFormatException ignored) {
            return false;
        }
    }

    private void tryAuthenticateAsBot(HttpServletRequest request) {
        String botSecret = request.getHeader(BOT_SECRET_HEADER);
        if (botSecret != null && botSecret.equals(appProperties.getBot().getSecret())) {
            var authority = new SimpleGrantedAuthority("ROLE_BOT");
            var auth = new UsernamePasswordAuthenticationToken("bot", null, List.of(authority));
            SecurityContextHolder.getContext().setAuthentication(auth);
        }
    }
}
