package ru.team42.monolith.rest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.dto.request.CreateKanbanBoardRequest;
import ru.team42.monolith.dto.response.KanbanBoardResponse;
import ru.team42.monolith.service.KanbanBoardService;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/api/boards")
@RequiredArgsConstructor
@Tag(name = "Kanban Boards", description = "Регистрация канбан-досок сторонних систем (YouGile, Jira, Trello...)")
public class KanbanBoardController {

    private final KanbanBoardService boardService;

    @Operation(
            summary = "Зарегистрировать канбан-доску",
            description = "Привязывает внешнюю доску к системе. " +
                    "statusMappingsJson: JSON-объект вида {\"external_status\": \"INTERNAL_STATUS\"}. " +
                    "Пример для YouGile: {\"В работе\": \"IN_PROGRESS\", \"Готово\": \"DONE\", \"Backlog\": \"OPEN\"}"
    )
    @PostMapping
    public ResponseEntity<KanbanBoardResponse> create(@Valid @RequestBody CreateKanbanBoardRequest request) {
        KanbanBoardResponse created = boardService.create(request);
        return ResponseUtils.created("/api/boards/" + created.id(), created);
    }

    @Operation(summary = "Получить доску по ID")
    @GetMapping("/{id}")
    public ResponseEntity<KanbanBoardResponse> getById(@PathVariable UUID id) {
        return ResponseUtils.ok(boardService.getById(id));
    }

    @Operation(summary = "Список активных досок")
    @GetMapping
    public ResponseEntity<List<KanbanBoardResponse>> listActive() {
        return ResponseUtils.ok(boardService.listActive());
    }
}
