package ru.team42.monolith.rest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import ru.team42.backend.web_common.dto.ErrorResponse;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.config.AppProperties;
import ru.team42.monolith.dto.request.CreateInviteRequest;
import ru.team42.monolith.dto.request.LoginRequest;
import ru.team42.monolith.dto.responce.AuthResponse;
import ru.team42.monolith.dto.responce.InviteResponse;
import ru.team42.monolith.service.AuthService;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
@Tag(name = "Auth", description = "Аутентификация через Telegram-бота")
public class AuthController {

    private final AuthService authService;
    private final AppProperties appProperties;

    @Operation(
            summary = "Создать инвайт-ссылку",
            description = "Вызывается Telegram-ботом. Генерирует одноразовый токен для входа пользователя. "
                    + "Требует секрет бота в заголовке X-Bot-Secret."
    )
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Инвайт создан",
                    content = @Content(schema = @Schema(implementation = InviteResponse.class))),
            @ApiResponse(responseCode = "403", description = "Неверный секрет бота",
                    content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
    })
    @PostMapping("/invite")
    public ResponseEntity<InviteResponse> createInvite(
            @Parameter(description = "Секрет бота (env BOT_SECRET)", required = true)
            @RequestHeader("X-Bot-Secret") String botSecret,
            @RequestBody(required = false) CreateInviteRequest request
    ) {
        if (!appProperties.getBot().getSecret().equals(botSecret)) {
            throw AppException.forbidden("Invalid bot secret");
        }
        return ResponseEntity.ok(authService.createInvite(request));
    }

    @Operation(
            summary = "Активировать инвайт / войти",
            description = "Пользователь передаёт одноразовый токен из инвайт-ссылки вместе со своими "
                    + "Telegram-данными. Токен сгорает после первого использования. "
                    + "Возвращает JWT для дальнейших запросов."
    )
    @ApiResponses({
            @ApiResponse(responseCode = "200", description = "Успешный вход, возвращает JWT",
                    content = @Content(schema = @Schema(implementation = AuthResponse.class))),
            @ApiResponse(responseCode = "400", description = "Невалидный запрос",
                    content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
            @ApiResponse(responseCode = "404", description = "Токен не найден или истёк",
                    content = @Content(schema = @Schema(implementation = ErrorResponse.class))),
    })
    @PostMapping("/login")
    public ResponseEntity<AuthResponse> login(@Valid @RequestBody LoginRequest request) {
        return ResponseEntity.ok(authService.activateInvite(request));
    }
}
