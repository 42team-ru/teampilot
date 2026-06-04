package ru.team42.monolith.security;

import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.slf4j.MDC;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.web.AuthenticationEntryPoint;
import org.springframework.security.web.access.AccessDeniedHandler;
import org.springframework.stereotype.Component;
import ru.team42.backend.web_common.dto.ErrorResponse;
import ru.team42.monolith.entity.User;
import tools.jackson.databind.ObjectMapper;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

@Component
@RequiredArgsConstructor
public class RestSecurityErrorHandler implements AuthenticationEntryPoint, AccessDeniedHandler {

    public static final String AUTH_FAILURE_DETAIL_ATTRIBUTE =
            RestSecurityErrorHandler.class.getName() + ".authFailureDetail";

    private final ObjectMapper objectMapper;

    @Override
    public void commence(
            HttpServletRequest request,
            HttpServletResponse response,
            AuthenticationException exception
    ) throws IOException {
        Object failureDetail = request.getAttribute(AUTH_FAILURE_DETAIL_ATTRIBUTE);
        String detail = failureDetail instanceof String message && !message.isBlank()
                ? message
                : "Authentication required: provide a valid X-Telegram-Id or X-Bot-Secret header";
        writeError(request, response, HttpStatus.UNAUTHORIZED, detail);
    }

    @Override
    public void handle(
            HttpServletRequest request,
            HttpServletResponse response,
            AccessDeniedException exception
    ) throws IOException, ServletException {
        Authentication authentication =
                org.springframework.security.core.context.SecurityContextHolder.getContext().getAuthentication();

        String detail = "Access denied: authenticated principal does not have permission for this operation";
        if (authentication != null && authentication.getPrincipal() instanceof User user) {
            detail = "Access denied for Telegram user %d: insufficient permissions for %s %s"
                    .formatted(user.getTelegramId(), request.getMethod(), request.getRequestURI());
        }

        writeError(request, response, HttpStatus.FORBIDDEN, detail);
    }

    private void writeError(
            HttpServletRequest request,
            HttpServletResponse response,
            HttpStatus status,
            String detail
    ) throws IOException {
        response.setStatus(status.value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        objectMapper.writeValue(
                response.getOutputStream(),
                new ErrorResponse(
                        status.value(),
                        status.getReasonPhrase(),
                        detail,
                        request.getRequestURI(),
                        traceId()
                )
        );
    }

    private String traceId() {
        String id = MDC.get("traceId");
        return id != null ? id : UUID.randomUUID().toString().replace("-", "").substring(0, 16);
    }
}
