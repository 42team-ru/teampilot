package ru.team42.monolith.rest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
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
import ru.team42.monolith.dto.request.GroupRequest;
import ru.team42.monolith.dto.response.GroupResponse;
import ru.team42.monolith.service.GroupService;

@RestController
@RequestMapping("/api/groups")
@RequiredArgsConstructor
@Tag(name = "Groups", description = "Управление группами и YouGile интеграцией")
public class GroupController {

    private final GroupService groupService;

    @Operation(summary = "Зарегистрировать или обновить группу")
    @PostMapping
    public ResponseEntity<GroupResponse> register(@RequestBody GroupRequest request) {
        GroupResponse response = groupService.register(request);
        return ResponseUtils.created("/api/groups/" + response.chatId(), response);
    }

    @Operation(summary = "Получить группу по chat ID")
    @GetMapping("/{chatId}")
    public ResponseEntity<GroupResponse> getByChatId(@PathVariable Long chatId) {
        return ResponseUtils.ok(
                groupService.findByChatId(chatId)
                        .orElseThrow(() -> AppException.notFound("Group with chatId %d not found".formatted(chatId)))
        );
    }

    @Operation(summary = "Деактивировать группу")
    @DeleteMapping("/{chatId}")
    public ResponseEntity<Void> deactivate(@PathVariable Long chatId) {
        groupService.deactivate(chatId);
        return ResponseUtils.noContent();
    }
}
