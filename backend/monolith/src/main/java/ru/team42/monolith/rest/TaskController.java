package ru.team42.monolith.rest;

import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import ru.team42.backend.web_common.dto.PageResponse;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.dto.response.TaskColumnResponse;
import ru.team42.monolith.dto.response.TaskResponse;
import ru.team42.monolith.entity.User;
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

    @PreAuthorize("isAuthenticated()")
    @GetMapping("/{id}")
    public ResponseEntity<TaskResponse> getById(@PathVariable UUID id) {
        return ResponseUtils.ok(TaskResponse.from(taskService.getById(id)));
    }

    @PreAuthorize("hasRole('BOT') or hasRole('SYSTEM_ADMIN')")
    @PostMapping("/{id}/sync")
    public ResponseEntity<TaskResponse> syncFromYouGile(@PathVariable UUID id) {
        return ResponseUtils.ok(TaskResponse.from(taskService.syncFromYouGile(id)));
    }

    @PreAuthorize("isAuthenticated()")
    @PostMapping("/{id}/approve")
    public ResponseEntity<TaskResponse> approve(
            @PathVariable UUID id,
            @AuthenticationPrincipal User currentUser) {
        return ResponseUtils.ok(TaskResponse.from(taskService.approve(id, currentUser)));
    }

    @PreAuthorize("hasRole('BOT') or hasRole('SYSTEM_ADMIN')")
    @PostMapping("/{id}/cancel")
    public ResponseEntity<TaskResponse> cancel(@PathVariable UUID id) {
        return ResponseUtils.ok(TaskResponse.from(taskService.cancel(id)));
    }

    @PreAuthorize("isAuthenticated()")
    @GetMapping("/my")
    public ResponseEntity<PageResponse<TaskResponse>> listMyTasks(
            @RequestParam Long assignee,
            @PageableDefault(size = 20) Pageable pageable) {
        Page<TaskResponse> page = taskService.listMyTasks(assignee, pageable)
                .map(TaskResponse::from);
        return ResponseUtils.page(PageResponse.fromPage(page));
    }

    @PreAuthorize("isAuthenticated()")
    @GetMapping("/columns")
    public ResponseEntity<List<TaskColumnResponse>> listColumns(@RequestParam Long chatId) {
        return ResponseUtils.ok(taskService.listColumns(chatId).stream()
                .map(TaskColumnResponse::from)
                .toList());
    }

    @PreAuthorize("isAuthenticated()")
    @GetMapping
    public ResponseEntity<PageResponse<TaskResponse>> list(
            @RequestParam(required = false) Long chatId,
            @RequestParam(required = false) Long assignee,
            @RequestParam(required = false) Boolean completed,
            @RequestParam(required = false) UUID columnId,
            @RequestParam(required = false) Boolean pendingApproval,
            @PageableDefault(size = 20) Pageable pageable) {

        Page<TaskResponse> page;
        if (columnId != null) {
            page = taskService.listByColumn(columnId, assignee, completed, pageable).map(TaskResponse::from);
        } else {
            page = taskService.list(chatId, assignee, completed, pendingApproval, pageable).map(TaskResponse::from);
        }
        return ResponseUtils.page(PageResponse.fromPage(page));
    }

// ============================================== ПАРАША ДЛЯ ТЕСТОВ ПОТОМ УДАЛИТЬ ==================================================

    @PreAuthorize("hasRole('SYSTEM_ADMIN')")
    @GetMapping("/yougile")
    public ResponseEntity<List<YouGileService.YouGileTaskResponse>> listFromYouGile(
            @RequestParam Long chatId) {
        return ResponseUtils.ok(taskService.listFromYouGile(chatId));
    }

    @PreAuthorize("hasRole('BOT') or hasRole('SYSTEM_ADMIN')")
    @PostMapping
    public ResponseEntity<TaskResponse> createTest(@RequestBody LlmTaskCreateEvent event) {
        return ResponseUtils.ok(TaskResponse.from(taskService.createFromLlmEvent(event)));
    }
}
