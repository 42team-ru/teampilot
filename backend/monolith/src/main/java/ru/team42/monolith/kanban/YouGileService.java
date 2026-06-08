package ru.team42.monolith.kanban;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.publisher.Mono;
import reactor.util.retry.Retry;
import ru.team42.monolith.client.yougile.api.DefaultApi;
import ru.team42.monolith.client.yougile.model.CreateChatMessageDto;
import ru.team42.monolith.client.yougile.model.CreateTaskDto;
import ru.team42.monolith.client.yougile.model.Deadline;
import ru.team42.monolith.client.yougile.model.TaskDto;
import ru.team42.monolith.client.yougile.model.TaskListDtoBase;
import ru.team42.monolith.client.yougile.model.UpdateTaskDto;
import ru.team42.monolith.client.yougile.model.WithIdDto;
import ru.team42.monolith.config.YougileClientConfig;
import ru.team42.monolith.entity.ChatMessage;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.enums.StickerType;
import ru.team42.monolith.mapper.TaskToYouGileMapper;

import java.math.BigDecimal;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.stream.Stream;

@Slf4j
@Service
@RequiredArgsConstructor
public class YouGileService {

    private final TaskToYouGileMapper taskToYouGileMapper;

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

        if (task.getStickers() != null && !task.getStickers().isEmpty()) {
            dto.setStickers(task.getStickers());
        }
        WithIdDto result = null;
        try {
            result = blockWithRetry(api.taskControllerCreate(dto));
            if (result == null) {
                return Optional.empty();
            }
            task.setExternalId(result.getId());
        } catch (Exception e) {
            log.error("Failed to create YouGile task for team {}: {}", team.getId(), e.getMessage());
        }
        log.info("Created YouGile task {} for local task {}", result.getId(), task.getId());


        for (ChatMessage sourceMessage : task.getSourceMessages()) {
            try {
                var userApi = YougileClientConfig.createAuthenticatedApi(sourceMessage.getTeamUser().getYougileUserApiKey());
                CreateChatMessageDto msgDto = new CreateChatMessageDto();
                msgDto.setText(sourceMessage.getText());
                msgDto.setLabel("");
                var resultMsg = blockWithRetry(userApi.chatMessageControllerSendMessage(task.getExternalId(), msgDto));
                if (resultMsg == null) {
                    log.warn("Failed to send chat message to YouGile task {}: empty response", task.getExternalId());
                } else {
                    log.info("Sent chat message to YouGile task {} for local message {}", task.getExternalId(), sourceMessage.getId());
                }
            } catch (Exception e) {
                log.error("Failed to send chat message to YouGile task {}: {}", task.getExternalId(), e.getMessage());
            }
        }
        return Optional.of(result.getId());
    }

    public record ColumnInfo(String id, String title, boolean deleted) {}

    public record StickerStateInfo(String id, String title) {}

    public record StickerInfo(String id, String title, StickerType type, List<StickerStateInfo> states) {}

    /**
     * Отправляет сообщение в чат задачи от имени пользователя (используется его личный API-ключ).
     */
    public Optional<String> sendChatMessage(String userApiKey, String externalTaskId, String text) {
        if (userApiKey == null || text == null) return Optional.empty();
        try {
            var api = YougileClientConfig.createAuthenticatedApi(userApiKey);
            CreateChatMessageDto dto = new CreateChatMessageDto();
            dto.setText(text);
            dto.setTextHtml(text);
            dto.setLabel("");
            var result = blockWithRetry(api.chatMessageControllerSendMessage(externalTaskId, dto));
            if (result != null) {
                log.info("Sent chat message to YouGile task {}", externalTaskId);
                return Optional.ofNullable(result.getId()).map(id -> id.toPlainString());
            }
        } catch (Exception e) {
            log.error("Failed to send chat message to YouGile task {}: {}", externalTaskId, e.getMessage());
        }
        return Optional.empty();
    }

    public List<YouGileChatMessageResponse> fetchChatMessages(Team team, String externalTaskId, Instant since) {
        if (team.getKanbanApiKey() == null) return List.of();
        try {
            BigDecimal sinceTs = since == null ? null
                    : BigDecimal.valueOf(since.toEpochMilli());
            var result = blockWithRetry(buildApi(team).chatMessageControllerSearch(
                    externalTaskId, false, BigDecimal.valueOf(100),
                    null, null, null, null, sinceTs, false));
            if (result == null) return List.of();
            return result.getContent().stream()
                    .filter(m -> !Boolean.TRUE.equals(m.getDeleted()))
                    .map(m -> new YouGileChatMessageResponse(
                            m.getId() != null ? m.getId().toPlainString() : null,
                            m.getFromUserId(),
                            m.getText(),
                            m.getEditTimestamp() != null
                                    ? Instant.ofEpochMilli(m.getEditTimestamp().longValue())
                                    : null))
                    .toList();
        } catch (Exception e) {
            log.warn("Failed to fetch chat messages for YouGile task {}: {}", externalTaskId, e.getMessage());
            return List.of();
        }
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
            dto.setCompleted(task.isCompleted());
            blockWithRetry(api.taskControllerUpdate(task.getExternalId(), dto));
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
            blockWithRetry(api.taskControllerUpdate(externalTaskId, dto));
            log.info("Deleted YouGile task {}", externalTaskId);
        } catch (Exception e) {
            log.error("Failed to delete YouGile task {}: {}", externalTaskId, e.getMessage());
        }
    }

    public Optional<YouGileTaskResponse> fetchTask(Team team, String externalTaskId) {
        try {
            var dto = blockWithRetry(buildApi(team).taskControllerGet(externalTaskId));
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
            var columns = blockWithRetry(api.columnControllerSearch(false, null, null, null, team.getKanbanId()));
            if (columns == null) return List.of();
            return columns.getContent().stream()
                    .flatMap(col -> fetchTasksForColumn(api, col.getId()))
                    .toList();
        } catch (Exception e) {
            log.error("Failed to fetch board tasks for team {}: {}", team.getId(), e.getMessage());
            throw new RuntimeException("YouGile board fetch failed for team " + team.getId(), e);
        }
    }

    public List<StickerInfo> fetchStickers(Team team) {
        if (team.getKanbanId() == null || team.getKanbanApiKey() == null) return List.of();
        DefaultApi api = buildApi(team);
        List<StickerInfo> result = new ArrayList<>();
        try {
            var sprint = blockWithRetry(api.sprintStickerControllerSearch(false, null, null, null, team.getKanbanId()));
            if (sprint != null) {
                sprint.getContent().forEach(s -> {
                    List<StickerStateInfo> states = s.getStates() == null ? List.of() :
                            s.getStates().stream()
                                    .map(st -> new StickerStateInfo(st.getId(), st.getName()))
                                    .toList();
                    result.add(new StickerInfo(s.getId(), s.getName(), StickerType.SPRINT, states));
                });
            }
        } catch (Exception e) {
            log.warn("Failed to fetch sprint stickers for team {}: {}", team.getId(), e.getMessage());
        }
        try {
            var strings = blockWithRetry(api.stringStickerControllerSearch(false, null, null, null, team.getKanbanId()));
            if (strings != null) {
                strings.getContent().forEach(s -> {
                    List<StickerStateInfo> states = s.getStates() == null ? List.of() :
                            s.getStates().stream()
                                    .map(st -> new StickerStateInfo(st.getId(), st.getName()))
                                    .toList();
                    result.add(new StickerInfo(s.getId(), s.getName(), StickerType.STRING, states));
                });
            }
        } catch (Exception e) {
            log.warn("Failed to fetch string stickers for team {}: {}", team.getId(), e.getMessage());
        }
        return result;
    }

    public List<ColumnInfo> fetchColumns(Team team) {
        if (team.getKanbanId() == null || team.getKanbanApiKey() == null) return List.of();
        try {
            var result = blockWithRetry(buildApi(team).columnControllerSearch(false, null, null, null, team.getKanbanId()));
            if (result == null) return List.of();
            return result.getContent().stream()
                    .map(col -> new ColumnInfo(col.getId(), col.getTitle(), Boolean.TRUE.equals(col.getDeleted())))
                    .toList();
        } catch (Exception e) {
            log.error("Failed to fetch columns for team {}: {}", team.getId(), e.getMessage());
            throw new RuntimeException("YouGile column fetch failed for team " + team.getId(), e);
        }
    }

    private YouGileTaskResponse toResponse(TaskListDtoBase t) {
        String responsible = (t.getAssigned() != null && !t.getAssigned().isEmpty())
                ? t.getAssigned().get(0) : null;
        return new YouGileTaskResponse(t.getId(), t.getTitle(), t.getColumnId(), responsible,
                t.getCreatedBy(), t.getDescription(), toInstant(t.getDeadline()),
                Boolean.TRUE.equals(t.getCompleted()));
    }

    private YouGileTaskResponse toResponse(TaskDto t) {
        String responsible = (t.getAssigned() != null && !t.getAssigned().isEmpty())
                ? t.getAssigned().get(0) : null;
        return new YouGileTaskResponse(t.getId(), t.getTitle(), t.getColumnId(), responsible,
                t.getCreatedBy(), t.getDescription(), toInstant(t.getDeadline()),
                Boolean.TRUE.equals(t.getCompleted()));
    }

    private Stream<YouGileTaskResponse> fetchTasksForColumn(DefaultApi api, String columnId) {
        try {
            var result = blockWithRetry(api.taskControllerSearch(false, BigDecimal.valueOf(100), null, null, columnId, null, null, null));
            if (result == null) return Stream.empty();
            return result.getContent().stream().map(this::toResponse);
        } catch (Exception e) {
            log.warn("Failed to fetch tasks for column {}: {}", columnId, e.getMessage());
            return Stream.empty();
        }
    }

    private Instant toInstant(Deadline d) {
        if (d == null || d.getDeadline() == null) return null;
        return Instant.ofEpochMilli(d.getDeadline().longValue());
    }

    private <T> T blockWithRetry(Mono<T> mono) {
        return mono
                .retryWhen(Retry.backoff(3, Duration.ofSeconds(2))
                        .filter(ex -> !(ex instanceof WebClientResponseException wcre
                                && wcre.getStatusCode().is4xxClientError())))
                .block();
    }

    public record YouGileTaskResponse(
            String id,
            String title,
            String columnId,
            String responsible,
            String createdBy,
            String description,
            Instant deadline,
            boolean completed
    ) {}

    private DefaultApi buildApi(Team team) {
        var client = YougileClientConfig.createApiClient();
        client.setBearerToken(team.getKanbanApiKey());
        return new DefaultApi(client);
    }

    public record YouGileChatMessageResponse(String id, String fromUserId, String text, Instant timestamp) {
    }
}
