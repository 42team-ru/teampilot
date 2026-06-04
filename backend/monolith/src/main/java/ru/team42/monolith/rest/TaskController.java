package ru.team42.monolith.rest;

import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import ru.team42.backend.web_common.dto.PageResponse;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.dto.response.TaskResponse;
import ru.team42.monolith.entity.enums.TaskStatus;
import ru.team42.monolith.event.LlmTaskCreateEvent;
import ru.team42.monolith.kanban.YouGileService;
import ru.team42.monolith.service.TaskService;

import java.util.List;

import java.util.UUID;

@RestController
@RequestMapping("/tasks")
@RequiredArgsConstructor
public class TaskController {

    private final TaskService taskService;

    /** Читает задачу из локальной БД */
    @GetMapping("/{id}")
    public ResponseEntity<TaskResponse> getById(@PathVariable UUID id) {
        return ResponseUtils.ok(TaskResponse.from(taskService.getById(id)));
    }

    /**
     * Идёт в YouGile по externalId, применяет diff (статус, название, исполнитель),
     * записывает историю статусов, возвращает актуальное состояние задачи.
     */
    @PostMapping("/{id}/sync")
    public ResponseEntity<TaskResponse> syncFromYouGile(@PathVariable UUID id) {
        return ResponseUtils.ok(TaskResponse.from(taskService.syncFromYouGile(id)));
    }

    @GetMapping
    public ResponseEntity<PageResponse<TaskResponse>> list(
            @RequestParam Long chatId,
            @RequestParam(required = false) TaskStatus status,
            @PageableDefault(size = 20) Pageable pageable) {

        Page<TaskResponse> page = taskService.listByTeam(chatId, status, pageable)
                .map(TaskResponse::from);
        return ResponseUtils.page(PageResponse.fromPage(page));
    }

// ============================================== ПАРАША ДЛЯ ТЕСТОВ ПОТОМ УДАЛИТЬ ==================================================

    @GetMapping("/yougile")
    public ResponseEntity<List<YouGileService.YouGileTaskResponse>> listFromYouGile(
            @RequestParam Long chatId) {
        return ResponseUtils.ok(taskService.listFromYouGile(chatId));
    }
    @PostMapping
    public ResponseEntity<TaskResponse> createTest(@RequestBody LlmTaskCreateEvent event) {
        return ResponseUtils.ok(TaskResponse.from(taskService.createFromLlmEvent(event)));
    }
}
