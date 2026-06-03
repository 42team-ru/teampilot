package ru.team42.monolith.rest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import ru.team42.monolith.dto.request.CreateInviteRequest;
import ru.team42.monolith.dto.request.LoginRequest;
import ru.team42.monolith.dto.response.AuthResponse;
import ru.team42.monolith.dto.response.InviteResponse;
import ru.team42.monolith.service.AuthService;

import java.util.UUID;

@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
@Tag(name = "Auth", description = "Аутентификация через Telegram-бота")
public class AuthController {

    private final AuthService authService;

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
}
