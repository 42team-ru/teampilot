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

import static ru.team42.monolith.security.RestSecurityErrorHandler.AUTH_FAILURE_DETAIL_ATTRIBUTE;

@Component
@RequiredArgsConstructor
public class TelegramAuthFilter extends OncePerRequestFilter {

    public static final String HEADER = "X-Telegram-Id";
    public static final String BOT_SECRET_HEADER = "X-Bot-Secret";

    private final UserRepository userRepository;
    private final AppProperties appProperties;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        String header = request.getHeader(HEADER);
        boolean authenticated = false;
        if (header != null && !header.isBlank()) {
            try {
                long telegramId = Long.parseLong(header);
                var user = userRepository.findByTelegramId(telegramId);
                if (user.isPresent()) {
                    var authority = new SimpleGrantedAuthority("ROLE_" + user.get().getSystemRole().name());
                    var auth = new UsernamePasswordAuthenticationToken(user.get(), null, List.of(authority));
                    SecurityContextHolder.getContext().setAuthentication(auth);
                } else {
                    request.setAttribute(
                            AUTH_FAILURE_DETAIL_ATTRIBUTE,
                            "User with Telegram ID %d not found".formatted(telegramId)
                    );
                }
                authenticated = SecurityContextHolder.getContext().getAuthentication() != null;
            } catch (NumberFormatException e) {
                request.setAttribute(
                        AUTH_FAILURE_DETAIL_ATTRIBUTE,
                        "Invalid X-Telegram-Id header '%s': expected an integer".formatted(header)
                );
            }
        }
        String botSecret = request.getHeader(BOT_SECRET_HEADER);
        if (!authenticated && botSecret != null) {
            if (botSecret.equals(appProperties.getBot().getSecret())) {
                var authority = new SimpleGrantedAuthority("ROLE_BOT");
                var auth = new UsernamePasswordAuthenticationToken("bot", null, List.of(authority));
                SecurityContextHolder.getContext().setAuthentication(auth);
                if (header == null || header.isBlank()) {
                    request.removeAttribute(AUTH_FAILURE_DETAIL_ATTRIBUTE);
                }
            } else {
                request.setAttribute(AUTH_FAILURE_DETAIL_ATTRIBUTE, "Invalid X-Bot-Secret header");
            }
        }
        chain.doFilter(request, response);
    }
}
