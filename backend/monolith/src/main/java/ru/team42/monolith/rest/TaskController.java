package ru.team42.monolith.rest;

import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import ru.team42.backend.web_common.dto.PageResponse;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.dto.response.TaskResponse;
import ru.team42.monolith.entity.enums.TaskStatus;
import ru.team42.monolith.service.TaskService;

import java.util.UUID;

@RestController
@RequestMapping("/api/tasks")
@RequiredArgsConstructor
public class TaskController {

    private final TaskService taskService;

    @GetMapping("/{id}")
    public ResponseEntity<TaskResponse> getById(@PathVariable UUID id) {
        return ResponseUtils.ok(TaskResponse.from(taskService.getById(id)));
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
}
