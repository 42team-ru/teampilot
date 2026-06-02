package ru.team42.monolith.security;

import jakarta.servlet.http.HttpSession;
import ru.team42.monolith.dto.TokenPair;
import ru.team42.monolith.repository.UserRepository;
import ru.team42.monolith.service.TokenService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.Authentication;
import org.springframework.security.oauth2.client.authentication.OAuth2AuthenticationToken;
import org.springframework.security.web.authentication.AuthenticationSuccessHandler;
import org.springframework.stereotype.Component;

import java.io.IOException;

@Component
@Slf4j
@RequiredArgsConstructor
public class OAuth2SuccessHandler implements AuthenticationSuccessHandler {

    // Фронтенд обрабатывает callback и сразу вызывает /me — токен не нужен в URL.
    private static final String CALLBACK_PATH = "/auth/oauth2/callback";

    @Value("${app.frontend-url:http://localhost:5173}")
    private String frontendUrl;

    private final TokenService tokenService;
    private final UserRepository userRepository;

    @Override
    public void onAuthenticationSuccess(HttpServletRequest request,
                                        HttpServletResponse response,
                                        Authentication authentication) throws IOException {
        OAuth2AuthenticationToken oauthToken = (OAuth2AuthenticationToken) authentication;
        AuthUserPrincipal principal = (AuthUserPrincipal) oauthToken.getPrincipal();

        var user = userRepository.findByUsername(principal.getUsername())
                .orElseThrow(() -> new IllegalStateException("Пользователь не найден после OAuth2 входа"));

        TokenPair tokenPair = tokenService.generateTokenPair(user);
        tokenService.setTokenCookies(response, tokenPair, request);

        HttpSession session = request.getSession(false);
        if (session != null) session.invalidate();

        log.info("OAuth2 вход через {}: {}", oauthToken.getAuthorizedClientRegistrationId(), user.getUsername());

        // Токен выставлен в HTTP-only cookie — в URL его не кладём (избегаем попадания в логи и history).
        response.sendRedirect(frontendUrl + CALLBACK_PATH);
    }
}
