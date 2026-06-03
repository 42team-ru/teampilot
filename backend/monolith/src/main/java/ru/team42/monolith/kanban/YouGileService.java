package ru.team42.monolith.kanban;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Getter;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.enums.TaskStatus;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class YouGileService {

    private static final String BASE_URL = "https://ru.yougile.com/api-v2";

    static final Map<TaskStatus, String> STATUS_TO_COLUMN = Map.of(
            TaskStatus.OPEN, "Backlog",
            TaskStatus.IN_PROGRESS, "В работе",
            TaskStatus.REVIEW, "На проверке",
            TaskStatus.BLOCKED, "Заблокировано",
            TaskStatus.DONE, "Готово",
            TaskStatus.CANCELLED, "Отменено"
    );

    private static final Map<String, TaskStatus> COLUMN_TO_STATUS;
    static {
        Map<String, TaskStatus> m = new HashMap<>();
        STATUS_TO_COLUMN.forEach((status, col) -> m.put(col, status));
        COLUMN_TO_STATUS = Map.copyOf(m);
    }

    private final RestClient restClient = RestClient.builder()
            .baseUrl(BASE_URL)
            .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
            .build();

    // boardId (kanbanId) → (columnName → columnId)
    private final Map<String, Map<String, String>> columnCache = new ConcurrentHashMap<>();

    public Optional<String> createTask(Team team, Task task) {
        try {
            String columnId = resolveColumnId(team, TaskStatus.IN_PROGRESS);
            if (columnId == null) {
                log.warn("No column id for IN_PROGRESS on board {}, skipping YouGile push", team.getKanbanId());
                return Optional.empty();
            }

            var body = new HashMap<String, Object>();
            body.put("title", task.getTitle());
            body.put("columnId", columnId);
            if (task.getDescription() != null) body.put("description", task.getDescription());
            if (task.getDeadline() != null) body.put("deadline", task.getDeadline().toEpochMilli());

            YouGileTaskResponse response = restClient.post()
                    .uri("/tasks")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + team.getKanbanApiKey())
                    .body(body)
                    .retrieve()
                    .body(YouGileTaskResponse.class);

            if (response != null && response.getId() != null) {
                log.info("Created YouGile task {} for team {}", response.getId(), team.getId());
                return Optional.of(response.getId());
            }
        } catch (Exception e) {
            log.error("Failed to create YouGile task for team {}: {}", team.getId(), e.getMessage());
            throw e;
        }
        return Optional.empty();
    }

    public void updateStatus(Team team, String externalTaskId, TaskStatus status) {
        try {
            String columnId = resolveColumnId(team, status);
            if (columnId == null) {
                log.warn("No column id for {} on board {}, skipping status update", status, team.getKanbanId());
                return;
            }
            restClient.put()
                    .uri("/tasks/{id}", externalTaskId)
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + team.getKanbanApiKey())
                    .body(Map.of("columnId", columnId))
                    .retrieve()
                    .toBodilessEntity();
            log.info("Updated YouGile task {} to column {} ({})", externalTaskId, columnId, status);
        } catch (Exception e) {
            log.error("Failed to update YouGile task {} status: {}", externalTaskId, e.getMessage());
            throw e;
        }
    }

    public Map<String, String> getExternalColumnIds(Team team, List<String> externalTaskIds) {
        Map<String, String> result = new HashMap<>();
        for (String taskId : externalTaskIds) {
            try {
                YouGileTaskResponse response = restClient.get()
                        .uri("/tasks/{id}", taskId)
                        .header(HttpHeaders.AUTHORIZATION, "Bearer " + team.getKanbanApiKey())
                        .retrieve()
                        .body(YouGileTaskResponse.class);
                if (response != null && response.getColumnId() != null) {
                    result.put(taskId, response.getColumnId());
                }
            } catch (Exception e) {
                log.warn("Failed to get YouGile task {} status: {}", taskId, e.getMessage());
            }
        }
        return result;
    }

    public TaskStatus resolveInternalStatus(Team team, String columnId) {
        String columnName = resolveColumnName(team, columnId);
        if (columnName == null) return TaskStatus.IN_PROGRESS;
        return COLUMN_TO_STATUS.getOrDefault(columnName, TaskStatus.IN_PROGRESS);
    }

    public String resolveColumnName(Team team, String columnId) {
        Map<String, String> columns = fetchColumns(team);
        return columns.entrySet().stream()
                .filter(e -> columnId.equals(e.getValue()))
                .map(Map.Entry::getKey)
                .findFirst()
                .orElse(null);
    }

    private String resolveColumnId(Team team, TaskStatus status) {
        String columnName = STATUS_TO_COLUMN.get(status);
        if (columnName == null) return null;
        Map<String, String> columns = fetchColumns(team);
        return columns.get(columnName);
    }

    private Map<String, String> fetchColumns(Team team) {
        return columnCache.computeIfAbsent(team.getKanbanId(), boardId -> {
            try {
                YouGileColumnsResponse response = restClient.get()
                        .uri("/string-boards/{id}/columns", boardId)
                        .header(HttpHeaders.AUTHORIZATION, "Bearer " + team.getKanbanApiKey())
                        .retrieve()
                        .body(YouGileColumnsResponse.class);
                if (response != null && response.getContent() != null) {
                    Map<String, String> map = new HashMap<>();
                    for (YouGileColumn col : response.getContent()) {
                        if (col.getId() != null && col.getTitle() != null) {
                            map.put(col.getTitle(), col.getId());
                        }
                    }
                    log.info("Cached {} columns for board {}", map.size(), boardId);
                    return map;
                }
            } catch (Exception e) {
                log.error("Failed to fetch columns for board {}: {}", boardId, e.getMessage());
            }
            return Map.of();
        });
    }

    /**
     * Fetches a single task from YouGile by its external ID.
     * Returns empty if the task is not found or the call fails.
     */
    public Optional<YouGileTaskResponse> fetchTask(Team team, String externalTaskId) {
        try {
            YouGileTaskResponse response = restClient.get()
                    .uri("/tasks/{id}", externalTaskId)
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + team.getKanbanApiKey())
                    .retrieve()
                    .body(YouGileTaskResponse.class);
            return Optional.ofNullable(response);
        } catch (Exception e) {
            log.error("Failed to fetch YouGile task {}: {}", externalTaskId, e.getMessage());
            return Optional.empty();
        }
    }

    public List<YouGileTaskResponse> fetchAllTasksForBoard(Team team) {
        Map<String, String> columns = fetchColumns(team);
        List<YouGileTaskResponse> all = new ArrayList<>();
        for (String columnId : columns.values()) {
            try {
                YouGileTaskListResponse response = restClient.get()
                        .uri(uri -> uri.path("/tasks").queryParam("columnId", columnId).build())
                        .header(HttpHeaders.AUTHORIZATION, "Bearer " + team.getKanbanApiKey())
                        .retrieve()
                        .body(YouGileTaskListResponse.class);
                if (response != null && response.getContent() != null) {
                    all.addAll(response.getContent());
                }
            } catch (Exception e) {
                log.warn("Failed to fetch tasks for column {}: {}", columnId, e.getMessage());
            }
        }
        log.info("Fetched {} tasks from board {} for team {}", all.size(), team.getKanbanId(), team.getId());
        return all;
    }

    public void evictColumnCache(String boardId) {
        columnCache.remove(boardId);
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    @Getter
    public static class YouGileTaskResponse {
        private String id;
        private String columnId;
        private String title;
        private Boolean completed;
        /** YouGile user ID of the responsible person (assignee) */
        private String responsible;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    @Getter
    static class YouGileColumnsResponse {
        private List<YouGileColumn> content;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    @Getter
    static class YouGileColumn {
        private String id;
        private String title;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    @Getter
    static class YouGileTaskListResponse {
        private List<YouGileTaskResponse> content;
    }
}
