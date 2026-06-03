package ru.team42.monolith.rest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.dto.request.UpdateTeamRequest;
import ru.team42.monolith.dto.response.TeamResponse;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.service.TeamService;

import java.util.List;

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
        return ResponseUtils.ok(teamService.getManagerTeams(currentUser.getTelegramId()));
    }

    @Operation(summary = "Обновить настройки команды (kanban, chatTitle, telegramChatId)")
    @PatchMapping("/{telegramChatId}")
    public ResponseEntity<TeamResponse> update(
            @PathVariable Long telegramChatId,
            @RequestBody UpdateTeamRequest request
    ) {
        return ResponseUtils.ok(teamService.update(telegramChatId, request));
    }
}
