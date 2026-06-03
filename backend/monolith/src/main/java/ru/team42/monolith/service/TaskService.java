package ru.team42.monolith.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.dto.request.CreateTaskRequest;
import ru.team42.monolith.dto.request.UpdateTaskStatusRequest;
import ru.team42.monolith.dto.response.TaskResponse;
import ru.team42.monolith.dto.response.TaskStatusResponse;
import ru.team42.monolith.entity.ChangeSource;
import ru.team42.monolith.entity.Group;
import ru.team42.monolith.entity.KanbanBoard;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.TaskStatus;
import ru.team42.monolith.entity.TaskStatusHistory;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.kanban.KanbanAdapterRegistry;
import ru.team42.monolith.mapper.TaskMapper;
import ru.team42.monolith.repository.GroupRepository;
import ru.team42.monolith.repository.KanbanBoardRepository;
import ru.team42.monolith.repository.TaskRepository;
import ru.team42.monolith.repository.TaskStatusHistoryRepository;
import ru.team42.monolith.repository.UserRepository;

import jakarta.persistence.criteria.JoinType;
import org.springframework.data.jpa.domain.Specification;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class TaskService {

    private final TaskRepository taskRepository;
    private final TaskStatusHistoryRepository historyRepository;
    private final KanbanBoardRepository boardRepository;
    private final UserRepository userRepository;
    private final GroupRepository groupRepository;
    private final KanbanAdapterRegistry adapterRegistry;
    private final ObjectMapper objectMapper;
    private final TaskMapper taskMapper;

    @Transactional
    public TaskResponse create(CreateTaskRequest request) {
        User creator = userRepository.findById(request.creatorId())
                .orElseThrow(() -> AppException.notFound("User %s not found".formatted(request.creatorId())));

        User assignee = request.assigneeId() != null
                ? userRepository.findById(request.assigneeId())
                        .orElseThrow(() -> AppException.notFound("Assignee %s not found".formatted(request.assigneeId())))
                : null;

        KanbanBoard board = request.boardId() != null
                ? boardRepository.findById(request.boardId())
                        .orElseThrow(() -> AppException.notFound("Board %s not found".formatted(request.boardId())))
                : null;

        Task task = taskRepository.save(taskMapper.toEntity(request, creator, assignee, board));
        recordHistory(task, null, TaskStatus.OPEN, null, null, ChangeSource.SYSTEM);

        if (task.getBoard() != null) {
            pushToExternalKanban(task);
        }

        return TaskResponse.from(task);
    }

    @Transactional(readOnly = true)
    public TaskResponse getById(UUID id) {
        return TaskResponse.from(findTask(id));
    }

    @Transactional(readOnly = true)
    public TaskStatusResponse getStatus(UUID id) {
        Task task = findTask(id);
        return new TaskStatusResponse(task.getId(), task.getStatus(), task.getExternalStatus());
    }

    @Transactional(readOnly = true)
    public List<TaskResponse> listByBoard(UUID boardId) {
        return taskRepository.findAllByBoardId(boardId).stream()
                .map(TaskResponse::from)
                .toList();
    }

    /**
     * Flexible list with optional filters. All params are nullable.
     * status="active" → all non-terminal statuses (bot /mytasks, /board).
     * status="DONE" (etc.) → exact match.
     */
    @Transactional(readOnly = true)
    public List<TaskResponse> list(Long assigneeTelegramId, String status, Long chatId, UUID boardId) {
        Specification<Task> spec = Specification.where(null);

        if (assigneeTelegramId != null) {
            spec = spec.and((root, query, cb) ->
                    cb.equal(root.join("assignee", JoinType.INNER).get("telegramId"), assigneeTelegramId));
        }

        if ("active".equalsIgnoreCase(status)) {
            var terminal = List.of(TaskStatus.DONE, TaskStatus.CANCELLED);
            spec = spec.and((root, query, cb) -> root.get("status").in(terminal).not());
        } else if (status != null) {
            try {
                TaskStatus s = TaskStatus.valueOf(status.toUpperCase());
                spec = spec.and((root, query, cb) -> cb.equal(root.get("status"), s));
            } catch (IllegalArgumentException ignored) {}
        }

        if (chatId != null) {
            spec = spec.and((root, query, cb) -> cb.equal(root.get("chatId"), chatId));
        }

        if (boardId != null) {
            spec = spec.and((root, query, cb) ->
                    cb.equal(root.join("board", JoinType.INNER).get("id"), boardId));
        }

        return taskRepository.findAll(spec).stream()
                .map(TaskResponse::from)
                .toList();
    }

    @Transactional
    public TaskResponse updateStatus(UUID id, UpdateTaskStatusRequest request) {
        Task task = findTask(id);
        TaskStatus previous = task.getStatus();
        TaskStatus next = request.status();

        if (previous == next) return TaskResponse.from(task);

        User changedBy = request.changedByUserId() != null
                ? userRepository.findById(request.changedByUserId())
                        .orElseThrow(() -> AppException.notFound("User %s not found".formatted(request.changedByUserId())))
                : null;

        task.setStatus(next);
        recordHistory(task, previous, next, null, changedBy,
                changedBy != null ? ChangeSource.USER : ChangeSource.LLM);
        syncStatusToExternal(task);

        return TaskResponse.from(taskRepository.save(task));
    }

    @Transactional
    public void syncStatusFromExternal(UUID taskId, String newExternalStatus) {
        Task task = findTask(taskId);
        TaskStatus mapped = resolveInternalStatus(task.getBoard(), newExternalStatus);

        if (task.getStatus() == mapped && newExternalStatus.equals(task.getExternalStatus())) return;

        TaskStatus previous = task.getStatus();
        task.setExternalStatus(newExternalStatus);
        task.setStatus(mapped);
        recordHistory(task, previous, mapped, newExternalStatus, null, ChangeSource.SCHEDULER);
        taskRepository.save(task);

        log.info("Task {} synced from external: {} -> {}", taskId, previous, mapped);
    }

    @Transactional
    public TaskResponse createFromLlm(String title, String description, Long chatId,
                                      String assigneeUsername, String sourceContext) {
        User assignee = assigneeUsername != null
                ? userRepository.findByTelegramLogin(assigneeUsername).orElse(null)
                : null;

        User creator = userRepository.findAllByRole(User.Role.SYSTEM_ADMIN).stream()
                .findFirst()
                .or(() -> userRepository.findAllByRole(User.Role.ADMIN).stream().findFirst())
                .orElseThrow(() -> AppException.internalError("No admin user to assign as task creator"));

        KanbanBoard board = groupRepository.findByChatId(chatId)
                .map(Group::getBoard)
                .filter(b -> b != null && b.isActive())
                .orElse(null);

        Task task = new Task();
        task.setCreator(creator);
        task.setAssignee(assignee);
        task.setBoard(board);
        task.setTitle(title);
        task.setDescription(description);
        task.setChatId(chatId);
        task.setSourceContext(sourceContext);
        task.setStatus(TaskStatus.OPEN);

        task = taskRepository.save(task);
        recordHistory(task, null, TaskStatus.OPEN, null, null, ChangeSource.LLM);

        if (task.getBoard() != null) {
            pushToExternalKanban(task);
        }

        return TaskResponse.from(task);
    }

    private void pushToExternalKanban(Task task) {
        KanbanBoard board = task.getBoard();
        if (!adapterRegistry.supports(board.getProvider())) {
            log.warn("No adapter for provider {}, skipping external push for task {}", board.getProvider(), task.getId());
            return;
        }
        adapterRegistry.get(board.getProvider())
                .createTask(board, task)
                .ifPresent(externalId -> {
                    task.setExternalTaskId(externalId);
                    taskRepository.save(task);
                });
    }

    private void syncStatusToExternal(Task task) {
        if (task.getBoard() == null || task.getExternalTaskId() == null) return;
        if (!adapterRegistry.supports(task.getBoard().getProvider())) return;

        String externalStatus = resolveExternalStatus(task.getBoard(), task.getStatus());
        if (externalStatus != null) {
            adapterRegistry.get(task.getBoard().getProvider())
                    .updateExternalStatus(task.getBoard(), task.getExternalTaskId(), externalStatus);
        }
    }

    private TaskStatus resolveInternalStatus(KanbanBoard board, String externalStatus) {
        if (board == null || board.getStatusMappingsJson() == null) return TaskStatus.IN_PROGRESS;
        try {
            Map<String, String> mappings = objectMapper.readValue(
                    board.getStatusMappingsJson(),
                    objectMapper.getTypeFactory().constructMapType(Map.class, String.class, String.class)
            );
            String internalName = mappings.get(externalStatus);
            if (internalName != null) return TaskStatus.valueOf(internalName);
        } catch (Exception e) {
            log.warn("Could not map external status '{}' for board {}: {}", externalStatus, board.getId(), e.getMessage());
        }
        return TaskStatus.IN_PROGRESS;
    }

    private String resolveExternalStatus(KanbanBoard board, TaskStatus status) {
        if (board.getStatusMappingsJson() == null) return null;
        try {
            Map<String, String> mappings = objectMapper.readValue(
                    board.getStatusMappingsJson(),
                    objectMapper.getTypeFactory().constructMapType(Map.class, String.class, String.class)
            );
            return mappings.entrySet().stream()
                    .filter(e -> status.name().equals(e.getValue()))
                    .map(Map.Entry::getKey)
                    .findFirst()
                    .orElse(null);
        } catch (Exception e) {
            log.warn("Could not resolve external status for {} on board {}", status, board.getId());
            return null;
        }
    }

    private void recordHistory(Task task, TaskStatus previous, TaskStatus next,
                               String externalStatus, User changedBy, ChangeSource source) {
        TaskStatusHistory history = new TaskStatusHistory();
        history.setTask(task);
        history.setPreviousStatus(previous);
        history.setNewStatus(next);
        history.setExternalStatus(externalStatus);
        history.setChangedByUser(changedBy);
        history.setChangeSource(source);
        historyRepository.save(history);
    }

    private Task findTask(UUID id) {
        return taskRepository.findById(id)
                .orElseThrow(() -> AppException.notFound("Task %s not found".formatted(id)));
    }
}
