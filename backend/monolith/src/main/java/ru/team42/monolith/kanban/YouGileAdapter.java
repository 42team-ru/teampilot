package ru.team42.monolith.kanban;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.Getter;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import ru.team42.monolith.entity.KanbanBoard;
import ru.team42.monolith.entity.KanbanProvider;
import ru.team42.monolith.entity.Task;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@Slf4j
@Component
@RequiredArgsConstructor
public class YouGileAdapter implements KanbanBoardAdapter {

    private static final String BASE_URL = "https://ru.yougile.com/api-v2";

    private final RestClient restClient = RestClient.builder()
            .baseUrl(BASE_URL)
            .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
            .build();

    private final ObjectMapper objectMapper;

    @Override
    public KanbanProvider supports() {
        return KanbanProvider.YOUGILE;
    }

    @Override
    public Optional<String> createTask(KanbanBoard board, Task task) {
        try {
            // statusMappingsJson maps "external status name" → "INTERNAL_STATUS"
            // We need the reverse: "INTERNAL_STATUS" → "external column id/name"
            // For YouGile we store column names as the external status key.
            // The "OPEN" internal status column is the default column for new tasks.
            String defaultColumnId = resolveColumnForStatus(board, "OPEN");

            var body = new HashMap<String, Object>();
            body.put("title", task.getTitle());
            body.put("columnId", defaultColumnId);
            if (task.getDescription() != null) {
                body.put("description", task.getDescription());
            }
            if (task.getDeadline() != null) {
                body.put("deadline", task.getDeadline().toEpochMilli());
            }

            YouGileTaskResponse response = restClient.post()
                    .uri("/tasks")
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + board.getAccessToken())
                    .body(body)
                    .retrieve()
                    .body(YouGileTaskResponse.class);

            if (response != null && response.getId() != null) {
                log.info("Created YouGile task {} for board {}", response.getId(), board.getId());
                return Optional.of(response.getId());
            }
        } catch (Exception e) {
            log.error("Failed to create YouGile task for board {}: {}", board.getId(), e.getMessage());
        }
        return Optional.empty();
    }

    @Override
    public Optional<String> getExternalStatus(KanbanBoard board, String externalTaskId) {
        try {
            YouGileTaskResponse response = restClient.get()
                    .uri("/tasks/{id}", externalTaskId)
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + board.getAccessToken())
                    .retrieve()
                    .body(YouGileTaskResponse.class);

            if (response != null && response.getColumnId() != null) {
                return Optional.of(response.getColumnId());
            }
        } catch (Exception e) {
            log.warn("Failed to get YouGile task {} status: {}", externalTaskId, e.getMessage());
        }
        return Optional.empty();
    }

    @Override
    public void updateExternalStatus(KanbanBoard board, String externalTaskId, String externalStatus) {
        try {
            var body = Map.of("columnId", externalStatus);
            restClient.put()
                    .uri("/tasks/{id}", externalTaskId)
                    .header(HttpHeaders.AUTHORIZATION, "Bearer " + board.getAccessToken())
                    .body(body)
                    .retrieve()
                    .toBodilessEntity();
            log.info("Updated YouGile task {} column to {}", externalTaskId, externalStatus);
        } catch (Exception e) {
            log.error("Failed to update YouGile task {} status: {}", externalTaskId, e.getMessage());
        }
    }

    @Override
    public Map<String, String> getExternalStatuses(KanbanBoard board, List<String> externalTaskIds) {
        Map<String, String> result = new HashMap<>();
        for (String taskId : externalTaskIds) {
            getExternalStatus(board, taskId).ifPresent(status -> result.put(taskId, status));
        }
        return result;
    }

    // Parses statusMappingsJson to find the external column id/name for a given internal status.
    // statusMappingsJson format: {"column-id-or-name": "INTERNAL_STATUS", ...}
    // This reverses that mapping to find external key for the requested internal status.
    private String resolveColumnForStatus(KanbanBoard board, String internalStatus) {
        try {
            if (board.getStatusMappingsJson() != null) {
                Map<String, String> mappings = objectMapper.readValue(
                        board.getStatusMappingsJson(),
                        objectMapper.getTypeFactory().constructMapType(Map.class, String.class, String.class)
                );
                for (Map.Entry<String, String> entry : mappings.entrySet()) {
                    if (internalStatus.equals(entry.getValue())) {
                        return entry.getKey();
                    }
                }
            }
        } catch (Exception e) {
            log.warn("Could not parse statusMappingsJson for board {}: {}", board.getId(), e.getMessage());
        }
        // Fall back to using externalBoardId as the column (caller should ensure it's correct)
        return board.getExternalBoardId();
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    @Getter
    static class YouGileTaskResponse {
        private String id;
        private String columnId;
        private String title;
        private Boolean completed;
    }
}
