package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.config.AppProperties;
import ru.team42.monolith.entity.*;
import ru.team42.monolith.entity.enums.TaskLocalStatus;
import ru.team42.monolith.entity.enums.TaskSyncStatus;
import ru.team42.monolith.entity.enums.TeamRole;
import ru.team42.monolith.event.LlmStatusChangeEvent;
import ru.team42.monolith.event.LlmTaskCreateEvent;
import ru.team42.monolith.event.LlmUpdateTaskEvent;
import ru.team42.monolith.kanban.YouGileService;
import ru.team42.monolith.mapper.LlmTaskUpdateMapper;
import ru.team42.monolith.repository.ChatMessageRepository;
import ru.team42.monolith.repository.TaskColumnRepository;
import ru.team42.monolith.repository.TaskRepository;
import ru.team42.monolith.repository.TaskStatusHistoryRepository;
import ru.team42.monolith.repository.TeamRepository;
import ru.team42.monolith.repository.TeamUserRepository;

import java.time.Instant;
import java.util.Collection;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class TaskService {

    private final TaskRepository taskRepository;
    private final TaskColumnRepository taskColumnRepository;
    private final TaskStatusHistoryRepository historyRepository;
    private final TeamRepository teamRepository;
    private final TeamUserRepository teamUserRepository;
    private final ChatMessageRepository chatMessageRepository;
    private final YouGileService youGileService;
    private final TaskEventPublisher taskEventPublisher;
    private final LlmTaskUpdateMapper llmTaskUpdateMapper;
    private final AppProperties appProperties;
    private final GamificationService gamificationService;

    @Transactional
    public Task createFromLlmEvent(LlmTaskCreateEvent event) {
        validateEvent(event);

        Team team = teamRepository.findById(UUID.fromString(event.getTeamId()))
                .orElseThrow(() -> AppException.notFound(
                        "Team not found for teamId %s".formatted(event.getTeamId())));

        List<TaskLocalStatus> activeStatuses = List.of(TaskLocalStatus.PENDING_APPROVAL, TaskLocalStatus.ACTIVE);
        if (taskRepository.existsByTeamIdAndTitleIgnoreCaseAndLocalStatusIn(team.getId(), event.getTitle(), activeStatuses)) {
            log.warn("Skipping duplicate task title='{}' teamId={}", event.getTitle(), event.getTeamId());
            return taskRepository.findFirstByTeamIdAndTitleIgnoreCaseAndLocalStatusIn(
                    team.getId(), event.getTitle(), activeStatuses).orElseThrow();
        }

        Task task = new Task();
        task.setTeam(team);
        task.setTitle(event.getTitle());
        task.setDescription(event.getDescription());
        task.setDeadline(event.getDeadline());
        task.setSyncStatus(TaskSyncStatus.PENDING_SYNC);

        if (event.getColumnId() != null) {
            try {
                taskColumnRepository.findById(UUID.fromString(event.getColumnId()))
                        .ifPresent(task::setColumn);
            } catch (IllegalArgumentException e) {
                log.warn("Invalid columnId '{}' in LlmTaskCreateEvent, skipping column assignment", event.getColumnId());
            }
        }

        if (event.getAssigneeId() != null) {
            resolveTeamUser(team, event.getAssigneeId()).ifPresent(task::setAssignee);
        }

        if (event.getSourceMessageIds() != null && !event.getSourceMessageIds().isEmpty()) {
            task.setSourceMessages(chatMessageRepository.findAllById(event.getSourceMessageIds()));
        }

        if (event.getStickers() != null && !event.getStickers().isEmpty()) {
            task.setStickers(event.getStickers());
        }

        boolean autoConfirm = event.getConfidence() >= appProperties.getLlm().getAutoConfirmThreshold();

        if (autoConfirm) {
            task.setLocalStatus(TaskLocalStatus.ACTIVE);
            Task saved = taskRepository.save(task);
            youGileService.createTask(saved.getTeam(), saved).ifPresent(externalId -> {
                saved.setExternalId(externalId);
                saved.setSyncStatus(TaskSyncStatus.SYNCED);
                taskRepository.save(saved);
            });
            taskEventPublisher.publishConfirmation(saved, true);
            taskEventPublisher.publishCreated(saved);
            log.info("Auto-confirmed task '{}' (confidence={})", saved.getTitle(), event.getConfidence());
            return saved;
        }

        task.setLocalStatus(TaskLocalStatus.PENDING_APPROVAL);
        return taskRepository.save(task);
    }

    @Transactional
    public Task cancel(UUID taskId) {
        Task task = taskRepository.findById(taskId)
                .orElseThrow(() -> AppException.notFound("Task %s not found".formatted(taskId)));

        if (task.getExternalId() != null) {
            youGileService.deleteTask(task.getTeam(), task.getExternalId());
        }

        task.setLocalStatus(TaskLocalStatus.DELETED_FROM_YOUGILE);
        task.setSyncStatus(TaskSyncStatus.PENDING_SYNC);
        Task saved = taskRepository.save(task);
        taskEventPublisher.publishCancelled(saved);
        return saved;
    }

    @Transactional
    public Task approve(UUID taskId, User user) {
        Task task = taskRepository.findById(taskId)
                .orElseThrow(() -> AppException.notFound("Task %s not found".formatted(taskId)));

        TeamUser membership = teamUserRepository.findByTeamIdAndUserId(task.getTeam().getId(), user.getId())
                .orElseThrow(() -> AppException.forbidden("You are not a member of this team"));
        if (membership.getRole() != TeamRole.MANAGER) {
            throw AppException.forbidden("Only a team manager can approve tasks");
        }

        if (task.getLocalStatus() != TaskLocalStatus.PENDING_APPROVAL) {
            throw AppException.badRequest("Task %s is not pending approval".formatted(taskId));
        }

        task.setLocalStatus(TaskLocalStatus.ACTIVE);
        final Task saved = taskRepository.save(task);

        youGileService.createTask(saved.getTeam(), saved).ifPresent(externalId -> {
            saved.setExternalId(externalId);
            saved.setSyncStatus(TaskSyncStatus.SYNCED);
            taskRepository.save(saved);
            taskEventPublisher.publishConfirmation(saved, false);
            taskEventPublisher.publishCreated(saved);
        });

        return saved;
    }

    @Transactional
    public void updateFromLlmEvent(LlmUpdateTaskEvent event) {
        if (event.getTaskId() == null) throw AppException.badRequest("taskId is required");

        Task task = taskRepository.findById(event.getTaskId())
                .orElseThrow(() -> AppException.notFound("Task %s not found".formatted(event.getTaskId())));

        String previousTitle = task.getTitle();
        String previousDescription = task.getDescription();
        Instant previousDeadline = task.getDeadline();
        UUID previousAssigneeId = task.getAssignee() != null ? task.getAssignee().getId() : null;

        llmTaskUpdateMapper.updateTaskFromEvent(event, task);

        TaskColumn newColumn = null;
        if (event.getColumnId() != null) {
            try {
                Optional<TaskColumn> colOpt = taskColumnRepository.findById(UUID.fromString(event.getColumnId()));
                if (colOpt.isPresent() && !colOpt.get().equals(task.getColumn())) {
                    TaskColumn prev = task.getColumn();
                    task.setColumn(colOpt.get());
                    newColumn = colOpt.get();
                    recordHistory(task, prev, colOpt.get(), telegramIdOf(task));
                }
            } catch (IllegalArgumentException e) {
                log.warn("Invalid columnId '{}' in LlmUpdateTaskEvent, skipping column assignment", event.getColumnId());
            }
        }

        boolean deleted = Boolean.TRUE.equals(event.getDeleted());
        if (deleted) {
            task.setDeleted(true);
            task.setLocalStatus(TaskLocalStatus.DELETED_FROM_YOUGILE);
        }

        if (Boolean.TRUE.equals(event.getCompleted())) {
            task.setCompleted(true);
        }

        if (event.getAssigneeId() != null) {
            resolveTeamUser(task.getTeam(), event.getAssigneeId())
                    .ifPresent(task::setAssignee);
        }

        UUID currentAssigneeId = task.getAssignee() != null ? task.getAssignee().getId() : null;
        boolean taskDetailsChanged = !Objects.equals(previousTitle, task.getTitle())
                || !Objects.equals(previousDescription, task.getDescription())
                || !Objects.equals(previousDeadline, task.getDeadline())
                || !Objects.equals(previousAssigneeId, currentAssigneeId);

        task = taskRepository.save(task);
        youGileService.updateTask(task.getTeam(), task);

        if (deleted) {
            taskEventPublisher.publishCancelled(task);
        } else {
            if (newColumn != null) {
                taskEventPublisher.publishColumnChanged(task, newColumn);
            }
            if (taskDetailsChanged) {
                taskEventPublisher.publishUpdated(task);
            }
        }
    }

    @Transactional(readOnly = true)
    public Task getById(UUID id) {
        return taskRepository.findById(id)
                .orElseThrow(() -> AppException.notFound("Task %s not found".formatted(id)));
    }

    @Transactional
    public Task syncFromYouGile(UUID id) {
        Task task = taskRepository.findById(id)
                .orElseThrow(() -> AppException.notFound("Task %s not found".formatted(id)));

        if (task.getExternalId() == null) {
            throw AppException.badRequest("Task %s has not been synced to YouGile yet".formatted(id));
        }

        Team team = task.getTeam();

        YouGileService.YouGileTaskResponse remote = youGileService.fetchTask(team, task.getExternalId())
                .orElseThrow(() -> AppException.internalError(
                        "YouGile did not return task " + task.getExternalId()));

        boolean changed = false;

        if (remote.columnId() != null) {
            Optional<TaskColumn> colOpt = taskColumnRepository
                    .findByTeamIdAndYouGileColumnId(team.getId(), remote.columnId());
            if (colOpt.isPresent() && !colOpt.get().equals(task.getColumn())) {
                TaskColumn prev = task.getColumn();
                task.setColumn(colOpt.get());
                recordHistory(task, prev, colOpt.get(), null);
                changed = true;
            }
        }

        if (remote.completed() != task.isCompleted()) {
            task.setCompleted(remote.completed());
            changed = true;
        }

        if (remote.title() != null && !remote.title().equals(task.getTitle())) {
            task.setTitle(remote.title());
            changed = true;
        }

        if (remote.responsible() != null) {
            Optional<TeamUser> tuOpt = teamUserRepository.findByTeamIdAndYougileUserId(
                    team.getId(), remote.responsible());
            if (tuOpt.isPresent() && !tuOpt.get().equals(task.getAssignee())) {
                task.setAssignee(tuOpt.get());
                changed = true;
            }
        }

        if (changed) {
            taskRepository.save(task);
        }

        log.info("Synced task {} from YouGile", id);
        return task;
    }

    @Transactional(readOnly = true)
    public Page<Task> list(Long chatId, Long assigneeTelegramId, Boolean completed, Boolean pendingApproval, Pageable pageable) {
        UUID teamId = null;
        if (chatId != null) {
            Team team = teamRepository.findByTelegramChatIdAndActiveTrue(chatId)
                    .orElseThrow(() -> AppException.notFound(
                            "Team not found for chatId %d".formatted(chatId)));
            teamId = team.getId();
        }

        if (teamId == null && assigneeTelegramId == null) {
            throw AppException.badRequest("chatId or assignee is required");
        }

        if (Boolean.TRUE.equals(pendingApproval)) {
            final UUID resolvedTeamId = teamId;
            if (resolvedTeamId == null) {
                throw AppException.badRequest("chatId is required for pendingApproval filter");
            }
            return taskRepository.findByTeamIdAndLocalStatus(resolvedTeamId, TaskLocalStatus.PENDING_APPROVAL, pageable);
        }

        if (Boolean.TRUE.equals(completed)) {
            if (teamId != null && assigneeTelegramId != null) {
                return taskRepository.findByTeamIdAndAssigneeUserTelegramIdAndCompletedTrueAndDeletedFalse(
                        teamId, assigneeTelegramId, pageable);
            }
            if (teamId != null) {
                return taskRepository.findByTeamIdAndCompletedTrueAndDeletedFalse(teamId, pageable);
            }
            return taskRepository.findByAssigneeUserTelegramIdAndCompletedTrueAndDeletedFalse(
                    assigneeTelegramId, pageable);
        }

        if (Boolean.FALSE.equals(completed)) {
            Collection<TaskLocalStatus> active = List.of(TaskLocalStatus.ACTIVE);
            if (teamId != null && assigneeTelegramId != null) {
                return taskRepository.findByTeamIdAndAssigneeUserTelegramIdAndLocalStatusInAndCompletedFalseAndDeletedFalse(
                        teamId, assigneeTelegramId, active, pageable);
            }
            if (teamId != null) {
                return taskRepository.findByTeamIdAndLocalStatusInAndCompletedFalseAndDeletedFalse(teamId, active, pageable);
            }
            return taskRepository.findByAssigneeUserTelegramIdAndLocalStatusInAndCompletedFalseAndDeletedFalse(
                    assigneeTelegramId, active, pageable);
        }

        // completed=null → все задачи без фильтра
        if (teamId != null && assigneeTelegramId != null) {
            return taskRepository.findByTeamIdAndAssigneeUserTelegramId(teamId, assigneeTelegramId, pageable);
        }
        if (teamId != null) {
            return taskRepository.findByTeamId(teamId, pageable);
        }
        return taskRepository.findByAssigneeUserTelegramId(assigneeTelegramId, pageable);
    }

    @Transactional(readOnly = true)
    public List<TaskColumn> listColumns(Long chatId) {
        Team team = teamRepository.findByTelegramChatIdAndActiveTrue(chatId)
                .orElseThrow(() -> AppException.notFound("Team not found for chatId %d".formatted(chatId)));
        return taskColumnRepository.findByTeamIdAndDeletedFalse(team.getId());
    }

    @Transactional(readOnly = true)
    public Page<Task> listByColumn(UUID columnId, Long assigneeTelegramId, Boolean completed, Pageable pageable) {
        if (Boolean.TRUE.equals(completed)) {
            if (assigneeTelegramId != null) {
                return taskRepository.findByColumnIdAndAssigneeUserTelegramIdAndCompletedTrueAndDeletedFalse(
                        columnId, assigneeTelegramId, pageable);
            }
            return taskRepository.findByColumnIdAndCompletedTrueAndDeletedFalse(columnId, pageable);
        }
        if (Boolean.FALSE.equals(completed)) {
            if (assigneeTelegramId != null) {
                return taskRepository.findByColumnIdAndAssigneeUserTelegramIdAndCompletedFalseAndDeletedFalse(
                        columnId, assigneeTelegramId, pageable);
            }
            return taskRepository.findByColumnIdAndCompletedFalseAndDeletedFalse(columnId, pageable);
        }
        if (assigneeTelegramId != null) {
            return taskRepository.findByColumnIdAndAssigneeUserTelegramIdAndDeletedFalse(
                    columnId, assigneeTelegramId, pageable);
        }
        return taskRepository.findByColumnIdAndDeletedFalse(columnId, pageable);
    }

    @Transactional(readOnly = true)
    public Page<Task> listMyTasks(Long telegramId, Pageable pageable) {
        return taskRepository.findByAssigneeUserTelegramIdAndCompletedFalseAndDeletedFalse(telegramId, pageable);
    }

    @Transactional(readOnly = true)
    public List<YouGileService.YouGileTaskResponse> listFromYouGile(Long chatId) {
        Team team = teamRepository.findByTelegramChatIdAndActiveTrue(chatId)
                .orElseThrow(() -> AppException.notFound(
                        "Team not found for chatId %d".formatted(chatId)));
        return youGileService.fetchAllTasksForBoard(team);
    }

    @Transactional
    public void handleStatusChange(LlmStatusChangeEvent event) {
        if (event.getTeamId() == null || event.getTaskId() == null) {
            log.warn("Skipping status change — missing teamId or taskId (action={})", event.getAction());
            return;
        }

        UUID taskId;
        try {
            taskId = UUID.fromString(event.getTaskId());
        } catch (IllegalArgumentException e) {
            log.warn("Invalid taskId '{}' in status change event", event.getTaskId());
            return;
        }

        Task task = taskRepository.findById(taskId).orElse(null);
        if (task == null) {
            log.warn("Task {} not found for status change action={}", taskId, event.getAction());
            return;
        }

        Team team = task.getTeam();
        log.info("Status change action={} for task '{}'", event.getAction(), task.getTitle());

        switch (event.getAction() == null ? "" : event.getAction()) {
            case "ASSIGN" -> applyAssign(team, task, event.getAssigneeId(), event.getColumnId());
            case "COMPLETE" -> applyComplete(team, task, event.getColumnId());
            case "CANCEL" -> cancel(task.getId());
            default -> log.warn("Unknown status change action: {}", event.getAction());
        }
    }

    private void applyAssign(Team team, Task task, Long assigneeId, String columnId) {
        if (assigneeId != null) {
            resolveTeamUser(team, assigneeId).ifPresent(task::setAssignee);
        }
        applyColumn(task, columnId, assigneeId);
        task.setLocalStatus(TaskLocalStatus.ACTIVE);
        Task saved = taskRepository.save(task);
        youGileService.updateTask(team, saved);
    }

    private void applyComplete(Team team, Task task, String columnId) {
        task.setCompleted(true);
        applyColumn(task, columnId, telegramIdOf(task));
        Task saved = taskRepository.save(task);
        youGileService.updateTask(team, saved);
        taskRepository.flush();
        try {
            gamificationService.onTaskCompleted(saved);
        } catch (Exception e) {
            log.warn("Gamification failed for task {}: {}", saved.getId(), e.getMessage());
        }
    }

    private void applyColumn(Task task, String columnId, Long changedByTelegramId) {
        if (columnId == null) return;
        try {
            taskColumnRepository.findById(UUID.fromString(columnId)).ifPresent(col -> {
                if (!col.equals(task.getColumn())) {
                    TaskColumn prev = task.getColumn();
                    task.setColumn(col);
                    recordHistory(task, prev, col, changedByTelegramId);
                    taskEventPublisher.publishColumnChanged(task, col);
                }
            });
        } catch (IllegalArgumentException e) {
            log.warn("Invalid columnId '{}' in status change event", columnId);
        }
    }

    private void validateEvent(LlmTaskCreateEvent event) {
        if (event.getTeamId() == null || event.getTeamId().isBlank()) throw AppException.badRequest("teamId is required");
        if (event.getTitle() == null || event.getTitle().isBlank())
            throw AppException.badRequest("title is required");
    }

    private Optional<TeamUser> resolveTeamUser(Team team, Long telegramId) {
        return teamUserRepository.findByTeamIdAndUserTelegramId(team.getId(), telegramId);
    }

    private void recordHistory(Task task, TaskColumn from, TaskColumn to, Long telegramId) {
        TaskStatusHistory h = new TaskStatusHistory();
        h.setTask(task);
        h.setFromColumn(from);
        h.setToColumn(to);
        h.setChangedByTelegramId(telegramId);
        historyRepository.save(h);
    }

    private Long telegramIdOf(Task task) {
        return task.getAssignee() != null ? task.getAssignee().getUser().getTelegramId() : null;
    }
}
