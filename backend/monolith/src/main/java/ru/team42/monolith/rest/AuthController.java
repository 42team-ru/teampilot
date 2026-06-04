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
import ru.team42.monolith.dto.request.LoginRequest;
import ru.team42.monolith.dto.request.YouGileConnectRequest;
import ru.team42.monolith.dto.request.YouGileCredentialsRequest;
import ru.team42.monolith.dto.response.AuthResponse;
import ru.team42.monolith.dto.response.InviteResponse;
import ru.team42.monolith.dto.response.TeamResponse;
import ru.team42.monolith.dto.response.YouGileBoardResponse;
import ru.team42.monolith.dto.response.YouGileCompanyResponse;
import ru.team42.monolith.dto.response.YouGileProjectResponse;
import ru.team42.monolith.service.AuthService;

import java.util.List;

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

    @Operation(
            summary = "Получить список компаний YouGile",
            description = "Шаг 1 подключения канбана. Возвращает компании по логину/паролю YouGile."
    )
    @PostMapping("/yougile/companies")
    public ResponseEntity<List<YouGileCompanyResponse>> listYouGileCompanies(
            @Valid @RequestBody YouGileCredentialsRequest request
    ) {
        return ResponseEntity.ok(authService.listYouGileCompanies(request));
    }

    @Operation(
            summary = "Подключить YouGile к команде",
            description = "Шаг 2: получает API-ключ для выбранной компании и сохраняет в команду."
    )
    @PostMapping("/yougile/connect")
    public ResponseEntity<TeamResponse> connectYouGile(
            @Valid @RequestBody YouGileConnectRequest request
    ) {
        return ResponseEntity.ok(authService.connectYouGile(request));
    }

    @Operation(
            summary = "Список проектов YouGile команды",
            description = "Шаг 3: после connect — выбрать проект для дальнейшего выбора доски."
    )
    @GetMapping("/yougile/projects")
    public ResponseEntity<List<YouGileProjectResponse>> listYouGileProjects(
            @RequestParam UUID teamId
    ) {
        return ResponseEntity.ok(authService.listYouGileProjects(teamId));
    }

    @Operation(
            summary = "Список досок YouGile команды",
            description = "Шаг 4: выбрать доску (kanbanId) — затем сохранить через PATCH /teams/{teamId}."
    )
    @GetMapping("/yougile/boards")
    public ResponseEntity<List<YouGileBoardResponse>> listYouGileBoards(
            @RequestParam UUID teamId,
            @RequestParam(required = false) String projectId
    ) {
        return ResponseEntity.ok(authService.listYouGileBoards(teamId, projectId));
    }
}
