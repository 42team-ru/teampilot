package ru.team42.monolith.rest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.dto.request.TeamRequest;
import ru.team42.monolith.dto.response.TeamResponse;
import ru.team42.monolith.service.TeamService;

@RestController
@RequestMapping("/api/teams")
@RequiredArgsConstructor
@Tag(name = "Teams", description = "Управление командами")
public class TeamController {

    private final TeamService teamService;

    @Operation(summary = "Создать команду")
    @PostMapping
    public ResponseEntity<TeamResponse> create(@Valid @RequestBody TeamRequest request) {
        TeamResponse response = teamService.create(request);
        return ResponseUtils.created("/api/teams/" + response.telegramChatId(), response);
    }

    @Operation(summary = "Получить команду по Telegram chat ID")
    @GetMapping("/{telegramChatId}")
    public ResponseEntity<TeamResponse> getByTelegramChatId(@PathVariable Long telegramChatId) {
        return ResponseUtils.ok(
                teamService.findByTelegramChatId(telegramChatId)
                        .orElseThrow(() -> AppException.notFound("Team with chatId %d not found".formatted(telegramChatId)))
        );
    }

    @Operation(summary = "Деактивировать команду")
    @DeleteMapping("/{telegramChatId}")
    public ResponseEntity<Void> deactivate(@PathVariable Long telegramChatId) {
        teamService.deactivate(telegramChatId);
        return ResponseUtils.noContent();
    }
}
