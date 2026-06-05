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
import ru.team42.monolith.event.LlmTaskCreateEvent;
import ru.team42.monolith.event.LlmUpdateTaskEvent;
import ru.team42.monolith.kanban.YouGileService;
import ru.team42.monolith.mapper.LlmTaskUpdateMapper;
import ru.team42.monolith.repository.TaskColumnRepository;
import ru.team42.monolith.repository.TaskRepository;
import ru.team42.monolith.repository.TaskStatusHistoryRepository;
import ru.team42.monolith.repository.TeamRepository;
import ru.team42.monolith.repository.TeamUserRepository;

import java.util.Collection;
import java.util.List;
import java.util.Locale;
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
    private final YouGileService youGileService;
    private final TaskEventPublisher taskEventPublisher;
    private final LlmTaskUpdateMapper llmTaskUpdateMapper;
    private final AppProperties appProperties;

    @Transactional
    public Task createFromLlmEvent(LlmTaskCreateEvent event) {
        validateEvent(event);

        Team team = teamRepository.findById(UUID.fromString(event.getTeamId()))
                .orElseThrow(() -> AppException.notFound(
                        "Team not found for teamId %s".formatted(event.getTeamId())));

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

        if (event.getAssigneeTelegramId() != null) {
            resolveTeamUser(team, event.getAssigneeTelegramId()).ifPresent(task::setAssignee);
        }
        if (event.getAuthorTelegramId() != null) {
            resolveTeamUser(team, event.getAuthorTelegramId()).ifPresent(task::setAuthor);
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
        return taskRepository.save(task);
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
        });

        return saved;
    }

    @Transactional
    public void updateFromLlmEvent(LlmUpdateTaskEvent event) {
        if (event.getTaskId() == null) throw AppException.badRequest("taskId is required");

        Task task = taskRepository.findById(event.getTaskId())
                .orElseThrow(() -> AppException.notFound("Task %s not found".formatted(event.getTaskId())));

        llmTaskUpdateMapper.updateTaskFromEvent(event, task);

        if (event.getColumnId() != null) {
            try {
                Optional<TaskColumn> colOpt = taskColumnRepository.findById(UUID.fromString(event.getColumnId()));
                if (colOpt.isPresent() && !colOpt.get().equals(task.getColumn())) {
                    TaskColumn prev = task.getColumn();
                    task.setColumn(colOpt.get());
                    recordHistory(task, prev, colOpt.get(), telegramIdOf(task));
                }
            } catch (IllegalArgumentException e) {
                log.warn("Invalid columnId '{}' in LlmUpdateTaskEvent, skipping column assignment", event.getColumnId());
            }
        }

        if (Boolean.TRUE.equals(event.getDeleted())) {
            task.setDeleted(true);
        }

        if (Boolean.TRUE.equals(event.getCompleted())) {
            task.setCompleted(true);
        }

        if (event.getAssigneeTelegramId() != null) {
            resolveTeamUser(task.getTeam(), event.getAssigneeTelegramId())
                    .ifPresent(task::setAssignee);
        }

        task = taskRepository.save(task);
        youGileService.updateTask(task.getTeam(), task);
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

        if (remote.title() != null && !remote.title().equals(task.getTitle())) {
            task.setTitle(remote.title());
            changed = true;
        }

        if (remote.responsible() != null) {
            teamUserRepository.findByTeamIdAndYougileUserId(team.getId(), remote.responsible())
                    .ifPresent(tu -> {
                        if (!tu.equals(task.getAssignee())) {
                            task.setAssignee(tu);
                        }
                    });
        }

        if (changed) {
            taskRepository.save(task);
        }

        log.info("Synced task {} from YouGile", id);
        return task;
    }

    @Transactional(readOnly = true)
    public Page<Task> list(Long chatId, Long assigneeTelegramId, String rawLocalStatus, Pageable pageable) {
        Collection<TaskLocalStatus> statuses = resolveLocalStatusFilter(rawLocalStatus);
        UUID teamId = null;
        if (chatId != null) {
            Team team = teamRepository.findByTelegramChatId(chatId)
                    .orElseThrow(() -> AppException.notFound(
                            "Team not found for chatId %d".formatted(chatId)));
            teamId = team.getId();
        }

        if (teamId == null && assigneeTelegramId == null) {
            throw AppException.badRequest("chatId or assignee is required");
        }

        if (teamId != null && assigneeTelegramId != null) {
            if (statuses != null) {
                return taskRepository.findByTeamIdAndAssigneeUserTelegramIdAndLocalStatusIn(
                        teamId, assigneeTelegramId, statuses, pageable);
            }
            return taskRepository.findByTeamIdAndAssigneeUserTelegramId(teamId, assigneeTelegramId, pageable);
        }

        if (teamId != null) {
            if (statuses != null) {
                return taskRepository.findByTeamIdAndLocalStatusIn(teamId, statuses, pageable);
            }
            return taskRepository.findByTeamId(teamId, pageable);
        }

        if (statuses != null) {
            return taskRepository.findByAssigneeUserTelegramIdAndLocalStatusIn(assigneeTelegramId, statuses, pageable);
        }
        return taskRepository.findByAssigneeUserTelegramId(assigneeTelegramId, pageable);
    }

    @Transactional(readOnly = true)
    public Page<Task> listMyTasks(Long telegramId, Pageable pageable) {
        return taskRepository.findByAssigneeUserTelegramIdAndCompletedFalseAndDeletedFalse(telegramId, pageable);
    }

    @Transactional(readOnly = true)
    public List<YouGileService.YouGileTaskResponse> listFromYouGile(Long chatId) {
        Team team = teamRepository.findByTelegramChatId(chatId)
                .orElseThrow(() -> AppException.notFound(
                        "Team not found for chatId %d".formatted(chatId)));
        return youGileService.fetchAllTasksForBoard(team);
    }

    private void validateEvent(LlmTaskCreateEvent event) {
        if (event.getTeamId() == null || event.getTeamId().isBlank()) throw AppException.badRequest("teamId is required");
        if (event.getTitle() == null || event.getTitle().isBlank())
            throw AppException.badRequest("title is required");
    }

    private Optional<TeamUser> resolveTeamUser(Team team, Long telegramId) {
        return teamUserRepository.findByTeamIdAndUserTelegramId(team.getId(), telegramId);
    }

    private Collection<TaskLocalStatus> resolveLocalStatusFilter(String raw) {
        if (raw == null || raw.isBlank()) return null;
        String normalized = raw.trim().toUpperCase(Locale.ROOT);
        try {
            return List.of(TaskLocalStatus.valueOf(normalized));
        } catch (IllegalArgumentException e) {
            throw AppException.badRequest("Unknown localStatus: " + raw);
        }
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
