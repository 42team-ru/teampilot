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
        if (header != null) {
            try {
                long telegramId = Long.parseLong(header);
                userRepository.findByTelegramId(telegramId).ifPresent(user -> {
                    var authority = new SimpleGrantedAuthority("ROLE_" + user.getSystemRole().name());
                    var auth = new UsernamePasswordAuthenticationToken(user, null, List.of(authority));
                    SecurityContextHolder.getContext().setAuthentication(auth);
                });
                authenticated = SecurityContextHolder.getContext().getAuthentication() != null;
            } catch (NumberFormatException ignored) {
            }
        }
        String botSecret = request.getHeader(BOT_SECRET_HEADER);
        if (!authenticated && botSecret != null && botSecret.equals(appProperties.getBot().getSecret())) {
            var authority = new SimpleGrantedAuthority("ROLE_BOT");
            var auth = new UsernamePasswordAuthenticationToken("bot", null, List.of(authority));
            SecurityContextHolder.getContext().setAuthentication(auth);
        }
        chain.doFilter(request, response);
    }
}
