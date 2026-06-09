package ru.team42.monolith.rest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.dto.request.CreatePendingTeamChatRequest;
import ru.team42.monolith.dto.request.UpdateMemberRoleRequest;
import ru.team42.monolith.dto.request.UpdateTeamRequest;
import ru.team42.monolith.dto.response.PendingTeamChatResponse;
import ru.team42.monolith.dto.response.TeamMemberResponse;
import ru.team42.monolith.dto.response.TeamResponse;
import ru.team42.monolith.dto.response.UploadedFileResponse;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.service.TeamService;

import java.util.List;
import java.util.UUID;

import static ru.team42.monolith.security.RestSecurityErrorHandler.AUTH_FAILURE_DETAIL_ATTRIBUTE;

@RestController
@RequestMapping("/teams")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "Team Manager", description = "Управление командами: доступно менеджеру команды")
public class TeamController {

    private final TeamService teamService;

    @Operation(summary = "Получить все команды, где текущий пользователь — менеджер")
    @GetMapping("/my")
    public ResponseEntity<List<TeamResponse>> getMyTeams(
            @Parameter(hidden = true) @AuthenticationPrincipal User currentUser,
            HttpServletRequest servletRequest
    ) {
        return ResponseUtils.ok(teamService.getManagerTeams(requireTelegramId(currentUser, servletRequest)));
    }

    @Operation(summary = "Получить все активные команды текущего пользователя")
    @GetMapping("/member-of")
    public ResponseEntity<List<TeamResponse>> getUserTeams(
            @Parameter(hidden = true) @AuthenticationPrincipal User currentUser,
            HttpServletRequest servletRequest
    ) {
        return ResponseUtils.ok(teamService.getUserTeams(requireTelegramId(currentUser, servletRequest)));
    }

    @Operation(summary = "Сохранить чат, куда менеджер добавил бота, для последующей привязки")
    @PostMapping("/pending-chats")
    public ResponseEntity<PendingTeamChatResponse> upsertPendingChat(
            @Parameter(hidden = true) @AuthenticationPrincipal User currentUser,
            HttpServletRequest servletRequest,
            @Valid @RequestBody CreatePendingTeamChatRequest request
    ) {
        return ResponseUtils.ok(teamService.upsertPendingChat(requireTelegramId(currentUser, servletRequest), request));
    }

    @Operation(summary = "Получить чаты, куда текущий менеджер добавил бота, но ещё не привязал команду")
    @GetMapping("/pending-chats")
    public ResponseEntity<List<PendingTeamChatResponse>> getMyPendingChats(
            @Parameter(hidden = true) @AuthenticationPrincipal User currentUser,
            HttpServletRequest servletRequest
    ) {
        log.info("Start handling getMyPendingChats for user {}, servletRequest {}", currentUser != null ? currentUser.getId() : null, servletRequest);
        var res = (teamService.getMyPendingChats(requireTelegramId(currentUser, servletRequest)));
        log.info("End handling getMyPendingChats for user {}, res {}", currentUser != null ? currentUser.getId() : null, res);
        return ResponseUtils.ok(res);
    }

    @Operation(summary = "Обновить настройки команды (kanban, chatTitle, telegramChatId)")
    @PatchMapping("/{teamId}")
    public ResponseEntity<TeamResponse> update(
            @Parameter(hidden = true) @AuthenticationPrincipal User currentUser,
            HttpServletRequest servletRequest,
            @PathVariable UUID teamId,
            @RequestBody UpdateTeamRequest request
    ) {
        return ResponseUtils.ok(teamService.update(teamId, request, requireTelegramId(currentUser, servletRequest)));
    }

    @Operation(summary = "Получить список участников команды")
    @GetMapping("/{teamId}/members")
    public ResponseEntity<List<TeamMemberResponse>> getMembers(
            @Parameter(hidden = true) @AuthenticationPrincipal User currentUser,
            HttpServletRequest servletRequest,
            @PathVariable UUID teamId
    ) {
        return ResponseUtils.ok(teamService.getTeamMembers(teamId, requireTelegramId(currentUser, servletRequest)));
    }

    @Operation(summary = "Получить список файлов команды с presigned URL для скачивания")
    @GetMapping("/{teamId}/files")
    public ResponseEntity<List<UploadedFileResponse>> getTeamFiles(
            @Parameter(hidden = true) @AuthenticationPrincipal User currentUser,
            HttpServletRequest servletRequest,
            @PathVariable UUID teamId
    ) {
        return ResponseUtils.ok(teamService.getTeamFiles(teamId, requireTelegramId(currentUser, servletRequest)));
    }

    @Operation(summary = "Удалить участника из команды")
    @DeleteMapping("/{teamId}/members/{teamUserId}")
    public ResponseEntity<Void> removeMember(
            @Parameter(hidden = true) @AuthenticationPrincipal User currentUser,
            HttpServletRequest servletRequest,
            @PathVariable UUID teamId,
            @PathVariable UUID teamUserId
    ) {
        teamService.removeMember(teamId, teamUserId, requireTelegramId(currentUser, servletRequest));
        return ResponseUtils.noContent();
    }

    @Operation(summary = "Изменить роль участника команды (менеджер → участник или наоборот)")
    @PatchMapping("/{teamId}/members/{teamUserId}/role")
    public ResponseEntity<TeamMemberResponse> updateMemberRole(
            @Parameter(hidden = true) @AuthenticationPrincipal User currentUser,
            HttpServletRequest servletRequest,
            @PathVariable UUID teamId,
            @PathVariable UUID teamUserId,
            @Valid @RequestBody UpdateMemberRoleRequest request
    ) {
        return ResponseUtils.ok(
                teamService.updateMemberRole(teamId, teamUserId, request.role(), requireTelegramId(currentUser, servletRequest))
        );
    }

    @Operation(summary = "Деактивировать команду")
    @DeleteMapping("/{telegramChatId}")
    public ResponseEntity<Void> deactivate(@PathVariable Long telegramChatId) {
        teamService.deactivate(telegramChatId);
        return ResponseUtils.noContent();
    }

    private Long requireTelegramId(User currentUser, HttpServletRequest servletRequest) {
        if (currentUser == null) {
            Object failureDetail = servletRequest.getAttribute(AUTH_FAILURE_DETAIL_ATTRIBUTE);
            if (failureDetail instanceof String detail && !detail.isBlank()) {
                if (detail.startsWith("User with Telegram ID")) {
                    throw AppException.notFound(detail);
                }
                throw AppException.unauthorized(detail);
            }
            throw AppException.unauthorized(
                    "Telegram user authentication required: provide a valid X-Telegram-Id header"
            );
        }
        return currentUser.getTelegramId();
    }

    private Long parseTelegramIdHeader(HttpServletRequest servletRequest) {
        String header = servletRequest.getHeader("X-Telegram-Id");
        if (header == null || header.isBlank()) {
            throw AppException.unauthorized("Telegram user authentication required: provide a valid X-Telegram-Id header");
        }
        try {
            return Long.parseLong(header);
        } catch (NumberFormatException e) {
            throw AppException.unauthorized("Invalid X-Telegram-Id header: expected an integer");
        }
    }
}
