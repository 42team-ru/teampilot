package ru.team42.monolith.rest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.dto.request.AdminCreateTeamRequest;
import ru.team42.monolith.dto.response.TeamResponse;
import ru.team42.monolith.service.TeamService;

@RestController
@RequestMapping("/admin")
@RequiredArgsConstructor
@Tag(name = "Admin", description = "Административные системные операции")
public class AdminController {

    private final TeamService teamService;

    @Operation(summary = "Создать команду с первым менеджером")
    @PostMapping("/teams")
    public ResponseEntity<TeamResponse> createTeam(@RequestBody AdminCreateTeamRequest request) {
        TeamResponse response = teamService.createWithAdmin(request);
        return ResponseUtils.created("/teams/" + response.telegramChatId(), response);
    }
}
