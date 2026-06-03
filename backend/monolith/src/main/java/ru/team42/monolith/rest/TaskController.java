package ru.team42.monolith.rest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.dto.request.CreateTaskRequest;
import ru.team42.monolith.dto.request.UpdateTaskStatusRequest;
import ru.team42.monolith.dto.response.TaskResponse;
import ru.team42.monolith.dto.response.TaskStatusResponse;
import ru.team42.monolith.service.TaskService;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/tasks")
@RequiredArgsConstructor
@Tag(name = "Tasks", description = "Управление задачами на канбан-досках")
public class TaskController {

    private final TaskService taskService;

    @Operation(summary = "Создать задачу",
            description = "Создаёт задачу и, если указана доска, регистрирует её во внешнем канбане.")
    @PostMapping
    public ResponseEntity<TaskResponse> create(@Valid @RequestBody CreateTaskRequest request) {
        TaskResponse created = taskService.create(request);
        return ResponseUtils.created("/api/tasks/" + created.id(), created);
    }

    @Operation(summary = "Получить задачу по ID")
    @GetMapping("/{id}")
    public ResponseEntity<TaskResponse> getById(@PathVariable UUID id) {
        return ResponseUtils.ok(taskService.getById(id));
    }

    @Operation(summary = "Получить статус задачи")
    @GetMapping("/{id}/status")
    public ResponseEntity<TaskStatusResponse> getStatus(@PathVariable UUID id) {
        return ResponseUtils.ok(taskService.getStatus(id));
    }

    @Operation(
            summary = "Изменить статус задачи",
            description = "Обновляет внутренний статус и синхронизирует его во внешний канбан. " +
                    "changedByUserId не передаётся для LLM/системных изменений."
    )
    @PatchMapping("/{id}/status")
    public ResponseEntity<TaskResponse> updateStatus(
            @PathVariable UUID id,
            @Valid @RequestBody UpdateTaskStatusRequest request
    ) {
        return ResponseUtils.ok(taskService.updateStatus(id, request));
    }

    @Operation(
            summary = "Список задач с фильтрами",
            description = """
                    Все параметры опциональны и комбинируются.
                    - assignee — Telegram ID исполнителя (/mytasks)
                    - status — "active" (всё не финальное) или точное имя статуса (OPEN, IN_PROGRESS, BLOCKED, REVIEW, DONE, CANCELLED)
                    - chatId — задачи из конкретного чата (/board)
                    - boardId — задачи конкретной доски
                    """
    )
    @GetMapping
    public ResponseEntity<List<TaskResponse>> list(
            @RequestParam(required = false) Long assignee,
            @RequestParam(required = false) String status,
            @RequestParam(required = false) Long chatId,
            @RequestParam(required = false) UUID boardId
    ) {
        return ResponseUtils.ok(taskService.list(assignee, status, chatId, boardId));
    }
}
