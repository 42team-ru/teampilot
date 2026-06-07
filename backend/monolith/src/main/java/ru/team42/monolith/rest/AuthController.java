package ru.team42.monolith.rest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.dto.request.CreateInviteRequest;
import ru.team42.monolith.dto.request.CreateUserRequest;
import ru.team42.monolith.dto.request.ConfirmExtensionLoginRequest;
import ru.team42.monolith.dto.request.LoginRequest;
import ru.team42.monolith.dto.request.TelegramOAuthRequest;
import ru.team42.monolith.dto.request.YouGileAuthRequest;
import ru.team42.monolith.dto.request.YouGileBoardSelectRequest;
import ru.team42.monolith.dto.response.AuthResponse;
import ru.team42.monolith.dto.response.ExtensionLoginStartResponse;
import ru.team42.monolith.dto.response.ExtensionLoginStatusResponse;
import ru.team42.monolith.dto.response.InviteResponse;
import ru.team42.monolith.dto.response.TeamResponse;
import ru.team42.monolith.dto.response.TelegramAuthResponse;
import ru.team42.monolith.dto.response.YouGileAuthResponse;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.service.AuthService;

import java.util.UUID;

@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
@Tag(name = "Auth", description = "Аутентификация через Telegram-бота")
public class AuthController {

    private final AuthService authService;

    @Operation(
            summary = "Войти через Telegram OAuth (расширение)",
            description = """
                    Принимает данные от Telegram Login Widget (id, first_name, auth_date, hash и др.).
                    Верифицирует подпись бота, создаёт или обновляет пользователя, возвращает JWT-токен.
                    Токен передавать в последующих запросах как: Authorization: Bearer <token>
                    """
    )
    @PostMapping("/telegram")
    public ResponseEntity<TelegramAuthResponse> telegramOAuth(@Valid @RequestBody TelegramOAuthRequest request) {
        return ResponseEntity.ok(authService.telegramOAuth(request));
    }

    @Operation(
            summary = "Создать одноразовый код входа для расширения",
            description = "Расширение показывает код пользователю. Пользователь отправляет /start <code> Telegram-боту."
    )
    @PostMapping("/extension-login")
    public ResponseEntity<ExtensionLoginStartResponse> createExtensionLogin() {
        return ResponseEntity.ok(authService.createExtensionLogin());
    }

    @Operation(
            summary = "Проверить статус одноразового кода входа для расширения",
            description = "Возвращает pending/confirmed/expired. При confirmed содержит JWT для расширения."
    )
    @GetMapping("/extension-login/{code}")
    public ResponseEntity<ExtensionLoginStatusResponse> getExtensionLogin(@PathVariable String code) {
        return ResponseEntity.ok(authService.getExtensionLogin(code));
    }

    @Operation(
            summary = "Подтвердить одноразовый код входа из Telegram-бота",
            description = "Вызывается только ботом с X-Bot-Secret после /start <code>."
    )
    @PreAuthorize("hasRole('BOT')")
    @PostMapping("/extension-login/{code}/confirm")
    public ResponseEntity<ExtensionLoginStatusResponse> confirmExtensionLogin(
            @PathVariable String code,
            @Valid @RequestBody ConfirmExtensionLoginRequest request
    ) {
        return ResponseEntity.ok(authService.confirmExtensionLogin(code, request));
    }

    @Operation(
            summary = "Создать пользователя",
            description = "Создаёт обычного пользователя по имени и фамилии."
    )
    @PostMapping({"/register", "/registration"})
    public ResponseEntity<AuthResponse> registerUser(@Valid @RequestBody CreateUserRequest request) {
        return ResponseUtils.created("/auth/registration", authService.registerUser(request));
    }

    @Operation(
            summary = "Получить инвайт-ссылку по chatId",
            description = "Вызывается ботом. По telegram chat ID возвращает ID команды для формирования ссылки."
    )
    @PostMapping("/invite")
    public ResponseEntity<InviteResponse> createInvite(@Valid @RequestBody CreateInviteRequest request) {
        return ResponseEntity.ok(authService.createInvite(request));
    }

    @Operation(
            summary = "Вступить в команду по инвайт-ссылке",
            description = "Пользователь переходит по ссылке. Создаёт пользователя (если новый) и добавляет в команду."
    )
    @PostMapping("/invite/{teamId}")
    public ResponseEntity<AuthResponse> joinTeam(
            @PathVariable UUID teamId,
            @Valid @RequestBody LoginRequest request
    ) {
        return ResponseEntity.ok(authService.joinTeam(teamId, request));
    }

    @Operation(
            summary = "Подключить YouGile (шаг 1)",
            description = """
                    Принимает chatId + логин/пароль YouGile.
                    • Если у пользователя одна компания — автоматически получает API-ключ, сохраняет и возвращает список досок (connected=true).
                    • Если компаний несколько — возвращает список на выбор (connected=false, companies=[...]).
                    • Если передан companyId — всегда подключается к ней сразу.
                    """
    )
    @PostMapping("/yougile/auth")
    public ResponseEntity<YouGileAuthResponse> yougileAuth(
            @Parameter(hidden = true) @AuthenticationPrincipal User currentUser,
            @Valid @RequestBody YouGileAuthRequest request
    ) {
        Long managerTelegramId = currentUser != null ? currentUser.getTelegramId() : null;
        return ResponseEntity.ok(authService.yougileAuth(request, managerTelegramId));
    }

    @Operation(
            summary = "Выбрать доску YouGile (шаг 2)",
            description = "Сохраняет выбранный boardId как kanbanId команды. Финальный шаг подключения."
    )
    @PostMapping("/yougile/board")
    public ResponseEntity<TeamResponse> yougileSelectBoard(
            @Valid @RequestBody YouGileBoardSelectRequest request
    ) {
        return ResponseEntity.ok(authService.yougileSelectBoard(request));
    }
}
