package ru.team42.monolith.rest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.dto.request.CreatePendingTeamChatRequest;
import ru.team42.monolith.dto.request.UpdateTeamRequest;
import ru.team42.monolith.dto.response.PendingTeamChatResponse;
import ru.team42.monolith.dto.response.TeamMemberResponse;
import ru.team42.monolith.dto.response.TeamResponse;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.service.TeamService;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/teams")
@RequiredArgsConstructor
@Tag(name = "Team Manager", description = "Управление командами: доступно менеджеру команды")
public class TeamController {

    private final TeamService teamService;

    @Operation(summary = "Получить все команды, где текущий пользователь — менеджер")
    @GetMapping("/my")
    public ResponseEntity<List<TeamResponse>> getMyTeams(
            @Parameter(hidden = true) @AuthenticationPrincipal User currentUser
    ) {
        return ResponseUtils.ok(teamService.getManagerTeams(requireTelegramId(currentUser)));
    }

    @Operation(summary = "Сохранить чат, куда менеджер добавил бота, для последующей привязки")
    @PostMapping("/pending-chats")
    public ResponseEntity<PendingTeamChatResponse> upsertPendingChat(
            @Parameter(hidden = true) @AuthenticationPrincipal User currentUser,
            @Valid @RequestBody CreatePendingTeamChatRequest request
    ) {
        return ResponseUtils.ok(teamService.upsertPendingChat(requireTelegramId(currentUser), request));
    }

    @Operation(summary = "Получить чаты, куда текущий менеджер добавил бота, но ещё не привязал команду")
    @GetMapping("/pending-chats")
    public ResponseEntity<List<PendingTeamChatResponse>> getMyPendingChats(
            @Parameter(hidden = true) @AuthenticationPrincipal User currentUser
    ) {
        return ResponseUtils.ok(teamService.getMyPendingChats(requireTelegramId(currentUser)));
    }

    @Operation(summary = "Обновить настройки команды (kanban, chatTitle, telegramChatId)")
    @PatchMapping("/{teamId}")
    public ResponseEntity<TeamResponse> update(
            @Parameter(hidden = true) @AuthenticationPrincipal User currentUser,
            @PathVariable UUID teamId,
            @RequestBody UpdateTeamRequest request
    ) {
        return ResponseUtils.ok(teamService.update(teamId, request, requireTelegramId(currentUser)));
    }

    @Operation(summary = "Получить список участников команды")
    @GetMapping("/{teamId}/members")
    public ResponseEntity<List<TeamMemberResponse>> getMembers(
            @Parameter(hidden = true) @AuthenticationPrincipal User currentUser,
            @PathVariable UUID teamId
    ) {
        return ResponseUtils.ok(teamService.getTeamMembers(teamId, requireTelegramId(currentUser)));
    }

    @Operation(summary = "Удалить участника из команды")
    @DeleteMapping("/{teamId}/members/{teamUserId}")
    public ResponseEntity<Void> removeMember(
            @Parameter(hidden = true) @AuthenticationPrincipal User currentUser,
            @PathVariable UUID teamId,
            @PathVariable UUID teamUserId
    ) {
        teamService.removeMember(teamId, teamUserId, requireTelegramId(currentUser));
        return ResponseUtils.noContent();
    }

    @Operation(summary = "Деактивировать команду")
    @DeleteMapping("/{telegramChatId}")
    public ResponseEntity<Void> deactivate(@PathVariable Long telegramChatId) {
        teamService.deactivate(telegramChatId);
        return ResponseUtils.noContent();
    }

    private Long requireTelegramId(User currentUser) {
        if (currentUser == null) {
            throw AppException.unauthorized("Telegram user is required");
        }
        return currentUser.getTelegramId();
    }
}
