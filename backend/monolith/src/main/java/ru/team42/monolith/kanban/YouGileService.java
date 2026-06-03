package ru.team42.monolith.kanban;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import ru.team42.monolith.client.yougile.api.DefaultApi;
import ru.team42.monolith.config.YougileClientConfig;
import ru.team42.monolith.client.yougile.model.ColumnListDtoBase;
import ru.team42.monolith.client.yougile.model.CreateTaskDto;
import ru.team42.monolith.client.yougile.model.Deadline;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.enums.TaskStatus;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Stream;

@Slf4j
@Service
public class YouGileService {



    // teamId → (TaskStatus → YouGile columnId), populated lazily, never persisted
    private final Map<UUID, Map<TaskStatus, String>> columnCache = new ConcurrentHashMap<>();

    public record YouGileTaskResponse(String id, String title, String columnId, String responsible) {
    }

    public Optional<String> createTask(Team team, Task task) {
        if (team.getKanbanId() == null || team.getKanbanApiKey() == null) {
            return Optional.empty();
        }
        DefaultApi api = buildApi(team);
        String columnId = resolveColumnId(team, api, task.getStatus());

        CreateTaskDto dto = new CreateTaskDto();
        dto.setTitle(task.getTitle());
        dto.setDescription(task.getDescription());
        dto.setColumnId(columnId);

        if (task.getDeadline() != null) {
            Deadline dl = new Deadline();
            dl.setDeadline(BigDecimal.valueOf(task.getDeadline().getEpochSecond()));
            dto.setDeadline(dl);
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

    public TaskStatus resolveInternalStatus(Team team, String columnId) {
        var cache = columnCache.get(team.getId());
        if (cache != null) {
            return cache.entrySet().stream()
                    .filter(e -> e.getValue().equals(columnId))
                    .map(Map.Entry::getKey)
                    .findFirst()
                    .orElse(TaskStatus.OPEN);
        }
        try {
            var column = buildApi(team).columnControllerGet(columnId).block();
            if (column != null) return titleToStatus(column.getTitle());
        } catch (Exception e) {
            log.warn("Failed to fetch column {} for team {}: {}", columnId, team.getId(), e.getMessage());
        }
        return TaskStatus.OPEN;
    }

    public String resolveColumnName(Team team, String columnId) {
        try {
            var column = buildApi(team).columnControllerGet(columnId).block();
            return column != null ? column.getTitle() : null;
        } catch (Exception e) {
            log.warn("Failed to fetch column {} name: {}", columnId, e.getMessage());
            return null;
        }
    }

    public Optional<YouGileTaskResponse> fetchTask(Team team, String externalTaskId) {
        try {
            var dto = buildApi(team).taskControllerGet(externalTaskId).block();
            if (dto == null) return Optional.empty();
            String responsible = (dto.getAssigned() != null && !dto.getAssigned().isEmpty())
                    ? dto.getAssigned().get(0) : null;
            return Optional.of(new YouGileTaskResponse(dto.getId(), dto.getTitle(), dto.getColumnId(), responsible));
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

    public void invalidateColumnCache(UUID teamId) {
        columnCache.remove(teamId);
    }

    private Stream<YouGileTaskResponse> fetchTasksForColumn(DefaultApi api, String columnId) {
        try {
            var result = api.taskControllerSearch(false, BigDecimal.valueOf(100), null, null, columnId, null, null, null).block();
            if (result == null) return Stream.empty();
            return result.getContent().stream().map(t -> {
                String responsible = (t.getAssigned() != null && !t.getAssigned().isEmpty())
                        ? t.getAssigned().get(0) : null;
                return new YouGileTaskResponse(t.getId(), t.getTitle(), t.getColumnId(), responsible);
            });
        } catch (Exception e) {
            log.warn("Failed to fetch tasks for column {}: {}", columnId, e.getMessage());
            return Stream.empty();
        }
    }

    private String resolveColumnId(Team team, DefaultApi api, TaskStatus status) {
        return columnCache
                .computeIfAbsent(team.getId(), id -> loadColumnMap(team, api))
                .get(status);
    }

    private Map<TaskStatus, String> loadColumnMap(Team team, DefaultApi api) {
        Map<TaskStatus, String> map = new ConcurrentHashMap<>();
        try {
            var columns = api.columnControllerSearch(false, null, null, null, team.getKanbanId()).block();
            if (columns == null)
                return map;
            List<ColumnListDtoBase> content = columns.getContent();
            for (ColumnListDtoBase col : content) {
                map.putIfAbsent(titleToStatus(col.getTitle()), col.getId());
            }
            if (!map.containsKey(TaskStatus.OPEN) && !content.isEmpty()) {
                map.put(TaskStatus.OPEN, content.get(0).getId());
            }
        } catch (Exception e) {
            log.error("Failed to load column map for team {}: {}", team.getId(), e.getMessage());
        }
        return map;
    }

    private DefaultApi buildApi(Team team) {
        var client = YougileClientConfig.createApiClient();
        client.setBearerToken(team.getKanbanApiKey());
        return new DefaultApi(client);
    }


    // TODO: ебать тут нахуячено нужно подумать как это исправить
    // FEATURE предлагаю кидать в LLM все колонки и куда его ставить в начале.
    private TaskStatus titleToStatus(String title) {
        if (title == null) return TaskStatus.OPEN;
        String lower = title.toLowerCase();
        if (lower.contains("готов") || lower.contains("done") || lower.contains("завершен") || lower.contains("выполн"))
            return TaskStatus.DONE;
        if (lower.contains("работ") || lower.contains("progress") || lower.contains("процесс"))
            return TaskStatus.IN_PROGRESS;
        if (lower.contains("review") || lower.contains("провер") || lower.contains("тест")) return TaskStatus.REVIEW;
        if (lower.contains("блок") || lower.contains("blocked")) return TaskStatus.BLOCKED;
        if (lower.contains("отмен") || lower.contains("cancel") || lower.contains("отказ")) return TaskStatus.CANCELLED;
        return TaskStatus.OPEN;
    }
}
