package ru.team42.monolith.rest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.dto.request.AdminCreateTeamRequest;
import ru.team42.monolith.dto.response.TeamResponse;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.enums.TaskLocalStatus;
import ru.team42.monolith.repository.TaskRepository;
import ru.team42.monolith.service.TaskEventPublisher;
import ru.team42.monolith.service.TeamService;

import java.util.List;

@Slf4j
@RestController
@RequestMapping("/admin")
@RequiredArgsConstructor
@Tag(name = "Admin", description = "Административные системные операции")
public class AdminController {

    private final TeamService teamService;
    private final TaskRepository taskRepository;
    private final TaskEventPublisher taskEventPublisher;

    @Operation(summary = "Создать команду с первым менеджером")
    @PostMapping("/teams")
    public ResponseEntity<TeamResponse> createTeam(@RequestBody AdminCreateTeamRequest request) {
        TeamResponse response = teamService.createWithAdmin(request);
        return ResponseUtils.created("/teams/" + response.telegramChatId(), response);
    }

    @Operation(summary = "Переиндексировать все активные задачи в Qdrant")
    @PostMapping("/reindex-tasks")
    public ResponseEntity<?> reindexTasks() {
        List<Task> tasks = taskRepository.findByDeletedFalseAndLocalStatus(TaskLocalStatus.ACTIVE);
        tasks.forEach(taskEventPublisher::publishImported);
        log.info("Reindex triggered for {} tasks", tasks.size());
        return ResponseUtils.ok(java.util.Map.of("reindexed", tasks.size()));
    }
}
