package ru.team42.monolith.kanban;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import ru.team42.monolith.client.yougile.api.DefaultApi;
import ru.team42.monolith.config.YougileClientConfig;
import ru.team42.monolith.client.yougile.model.CreateTaskDto;
import ru.team42.monolith.client.yougile.model.Deadline;
import ru.team42.monolith.client.yougile.model.UpdateTaskDto;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.mapper.TaskToYouGileMapper;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.stream.Stream;

@Slf4j
@Service
@RequiredArgsConstructor
public class YouGileService {

    private final TaskToYouGileMapper taskToYouGileMapper;

    public record YouGileTaskResponse(
            String id,
            String title,
            String columnId,
            String responsible,
            String createdBy,
            String description,
            java.time.Instant deadline,
            boolean completed
    ) {}

    public record ColumnInfo(String id, String title) {}

    public Optional<String> createTask(Team team, Task task) {
        if (team.getKanbanId() == null || team.getKanbanApiKey() == null) {
            return Optional.empty();
        }
        DefaultApi api = buildApi(team);

        CreateTaskDto dto = new CreateTaskDto();
        dto.setTitle(task.getTitle());
        dto.setDescription(task.getDescription());

        String columnId = task.getColumn() != null ? task.getColumn().getYouGileColumnId() : null;
        dto.setColumnId(columnId);

        if (task.getDeadline() != null) {
            Deadline dl = new Deadline();
            dl.setDeadline(BigDecimal.valueOf(task.getDeadline().toEpochMilli()));
            dto.setDeadline(dl);
        }

        if (task.getAssignee() != null && task.getAssignee().getYougileUserId() != null) {
            dto.setAssigned(List.of(task.getAssignee().getYougileUserId()));
        }

        try {
            var result = api.taskControllerCreate(dto).block();
            if (result != null) {
                log.info("Created YouGile task {} for local task {}", result.getId(), task.getId());
                return Optional.of(result.getId());
            }
        } catch (Exception e) {
            log.error("Failed to create YouGile task for team {}: {}", team.getId(), e.getMessage());
        }
        return Optional.empty();
    }

    public void updateTask(Team team, Task task) {
        if (team.getKanbanId() == null || team.getKanbanApiKey() == null) return;
        if (task.getExternalId() == null) {
            log.error("Cannot update YouGile task for local task {} — no externalId yet", task.getId());
            return;
        }
        DefaultApi api = buildApi(team);

        try {
            var dto = taskToYouGileMapper.toUpdateDto(task);
            api.taskControllerUpdate(task.getExternalId(), dto).block();
            log.info("Updated YouGile task {} for local task {}", task.getExternalId(), task.getId());
        } catch (Exception e) {
            log.error("Failed to update YouGile task {} for local task {}: {}",
                    task.getExternalId(), task.getId(), e.getMessage());
        }
    }

    public void deleteTask(Team team, String externalTaskId) {
        if (team.getKanbanId() == null || team.getKanbanApiKey() == null) return;
        DefaultApi api = buildApi(team);
        try {
            UpdateTaskDto dto = new UpdateTaskDto();
            dto.setDeleted(true);
            api.taskControllerUpdate(externalTaskId, dto).block();
            log.info("Deleted YouGile task {}", externalTaskId);
        } catch (Exception e) {
            log.error("Failed to delete YouGile task {}: {}", externalTaskId, e.getMessage());
        }
    }

    public Optional<YouGileTaskResponse> fetchTask(Team team, String externalTaskId) {
        try {
            var dto = buildApi(team).taskControllerGet(externalTaskId).block();
            if (dto == null) return Optional.empty();
            return Optional.of(toResponse(dto));
        } catch (Exception e) {
            log.warn("Failed to fetch YouGile task {}: {}", externalTaskId, e.getMessage());
            return Optional.empty();
        }
    }

    public List<YouGileTaskResponse> fetchAllTasksForBoard(Team team) {
        if (team.getKanbanId() == null || team.getKanbanApiKey() == null) return List.of();
        DefaultApi api = buildApi(team);
        try {
            var columns = api.columnControllerSearch(false, null, null, null, team.getKanbanId()).block();
            if (columns == null) return List.of();
            return columns.getContent().stream()
                    .flatMap(col -> fetchTasksForColumn(api, col.getId()))
                    .toList();
        } catch (Exception e) {
            log.error("Failed to fetch board tasks for team {}: {}", team.getId(), e.getMessage());
            return List.of();
        }
    }

    public List<ColumnInfo> fetchColumns(Team team) {
        if (team.getKanbanId() == null || team.getKanbanApiKey() == null) return List.of();
        try {
            var result = buildApi(team).columnControllerSearch(false, null, null, null, team.getKanbanId()).block();
            if (result == null) return List.of();
            return result.getContent().stream()
                    .map(col -> new ColumnInfo(col.getId(), col.getTitle()))
                    .toList();
        } catch (Exception e) {
            log.warn("Failed to fetch columns for team {}: {}", team.getId(), e.getMessage());
            return List.of();
        }
    }

    private Stream<YouGileTaskResponse> fetchTasksForColumn(DefaultApi api, String columnId) {
        try {
            var result = api.taskControllerSearch(false, BigDecimal.valueOf(100), null, null, columnId, null, null, null).block();
            if (result == null) return Stream.empty();
            return result.getContent().stream().map(this::toResponse);
        } catch (Exception e) {
            log.warn("Failed to fetch tasks for column {}: {}", columnId, e.getMessage());
            return Stream.empty();
        }
    }

    private YouGileTaskResponse toResponse(ru.team42.monolith.client.yougile.model.TaskListDtoBase t) {
        String responsible = (t.getAssigned() != null && !t.getAssigned().isEmpty())
                ? t.getAssigned().get(0) : null;
        return new YouGileTaskResponse(t.getId(), t.getTitle(), t.getColumnId(), responsible,
                t.getCreatedBy(), t.getDescription(), toInstant(t.getDeadline()),
                Boolean.TRUE.equals(t.getCompleted()));
    }

    private YouGileTaskResponse toResponse(ru.team42.monolith.client.yougile.model.TaskDto t) {
        String responsible = (t.getAssigned() != null && !t.getAssigned().isEmpty())
                ? t.getAssigned().get(0) : null;
        return new YouGileTaskResponse(t.getId(), t.getTitle(), t.getColumnId(), responsible,
                t.getCreatedBy(), t.getDescription(), toInstant(t.getDeadline()),
                Boolean.TRUE.equals(t.getCompleted()));
    }

    private java.time.Instant toInstant(ru.team42.monolith.client.yougile.model.Deadline d) {
        if (d == null || d.getDeadline() == null) return null;
        return java.time.Instant.ofEpochMilli(d.getDeadline().longValue());
    }

    private DefaultApi buildApi(Team team) {
        var client = YougileClientConfig.createApiClient();
        client.setBearerToken(team.getKanbanApiKey());
        return new DefaultApi(client);
    }
}
