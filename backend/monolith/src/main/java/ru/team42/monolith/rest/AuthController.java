package ru.team42.monolith.rest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import ru.team42.monolith.dto.request.CreateInviteRequest;
import ru.team42.monolith.dto.request.CreateUserRequest;
import ru.team42.monolith.dto.request.LoginRequest;
import ru.team42.monolith.dto.request.YouGileAuthRequest;
import ru.team42.monolith.dto.request.YouGileBoardSelectRequest;
import ru.team42.monolith.dto.response.AuthResponse;
import ru.team42.monolith.dto.response.InviteResponse;
import ru.team42.monolith.dto.response.TeamResponse;
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
            summary = "Создать пользователя",
            description = "Создаёт обычного пользователя по имени и фамилии."
    )
    @PostMapping("/register")
    public ResponseEntity<AuthResponse> registerUser(@Valid @RequestBody CreateUserRequest request) {
        return ResponseUtils.created("/auth/register", authService.registerUser(request));
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
            @Valid @RequestBody YouGileAuthRequest request
    ) {
        return ResponseEntity.ok(authService.yougileAuth(request));
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
