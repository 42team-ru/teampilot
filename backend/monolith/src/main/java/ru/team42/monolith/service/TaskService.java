package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.TaskStatusHistory;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.entity.enums.TaskStatus;
import ru.team42.monolith.entity.enums.TaskSyncStatus;
import ru.team42.monolith.entity.enums.TaskLocalStatus;
import ru.team42.monolith.event.LlmTaskCreateEvent;
import ru.team42.monolith.event.LlmUpdateTaskEvent;
import ru.team42.monolith.kanban.YouGileService;
import ru.team42.monolith.mapper.LlmTaskUpdateMapper;
import ru.team42.monolith.repository.TaskRepository;
import ru.team42.monolith.repository.TaskStatusHistoryRepository;
import ru.team42.monolith.repository.TeamRepository;
import ru.team42.monolith.repository.TeamUserRepository;

import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class TaskService {

    private static final int YOUGILE_MAX_RETRIES = 3;
    private static final long RETRY_BASE_MS = 1_000;
    private static final List<TaskStatus> ACTIVE_STATUSES = List.of(
            TaskStatus.OPEN,
            TaskStatus.IN_PROGRESS,
            TaskStatus.REVIEW,
            TaskStatus.BLOCKED
    );

    private final TaskRepository taskRepository;
    private final TaskStatusHistoryRepository historyRepository;
    private final TeamRepository teamRepository;
    private final TeamUserRepository teamUserRepository;
    private final YouGileService youGileService;
    private final TaskEventPublisher taskEventPublisher;
    private final LlmTaskUpdateMapper llmTaskUpdateMapper;

    @Transactional
    public Task createFromLlmEvent(LlmTaskCreateEvent event) {
        validateEvent(event);

        Team team = teamRepository.findByTelegramChatId(event.getChatId())
                .orElseThrow(() -> AppException.notFound(
                        "Team not found for chatId %d".formatted(event.getChatId())));

        Task task = new Task();
        task.setTeam(team);
        task.setTitle(event.getTitle());
        task.setDescription(event.getDescription());
        task.setDeadline(event.getDeadline());
        task.setStatus(TaskStatus.IN_PROGRESS);
        task.setExternalColumnId(event.getColumnId());
        task.setSyncStatus(TaskSyncStatus.PENDING_SYNC);

        if (event.getAssigneeTelegramId() != null) {
            resolveTeamUser(team, event.getAssigneeTelegramId()).ifPresent(task::setAssignee);
        }
        if (event.getAuthorTelegramId() != null) {
            resolveTeamUser(team, event.getAuthorTelegramId()).ifPresent(task::setAuthor);
        }

        task = taskRepository.save(task);
        recordHistory(task, null, TaskStatus.IN_PROGRESS, null);

        youGileService.createTask(team, task);

        return task;
    }

    @Transactional
    public void updateFromLlmEvent(LlmUpdateTaskEvent event) {
        if (event.getTaskId() == null) throw AppException.badRequest("taskId is required");

        Task task = taskRepository.findById(event.getTaskId())
                .orElseThrow(() -> AppException.notFound("Task %s not found".formatted(event.getTaskId())));

        llmTaskUpdateMapper.updateTaskFromEvent(event, task);

        if (Boolean.TRUE.equals(event.getDeleted())) {
            task.setLocalStatus(TaskLocalStatus.DELETED_FROM_YOUGILE);
        }

        if (Boolean.TRUE.equals(event.getCompleted())) {
            TaskStatus prev = task.getStatus();
            task.setStatus(TaskStatus.DONE);
            if (prev != TaskStatus.DONE) {
                recordHistory(task, prev, TaskStatus.DONE, null);
            }
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
/*
        ru.team42.monolith.kanban.YouGileService.YouGileTaskResponse remote =
                youGileService.fetchTask(team, task.getExternalId())
                        .orElseThrow(() -> AppException.internalError(
                                "YouGile did not return task " + task.getExternalId()));

        boolean changed = false;

        if (remote.getColumnId() != null) {
            TaskStatus newStatus = youGileService.resolveInternalStatus(team, remote.getColumnId());
            if (newStatus != task.getStatus()) {
                recordHistory(task, task.getStatus(), newStatus, null);
                task.setStatus(newStatus);
                changed = true;
            }
        }

        if (remote.getTitle() != null && !remote.getTitle().equals(task.getTitle())) {
            task.setTitle(remote.getTitle());
            changed = true;
        }

        if (remote.getResponsible() != null) {
            teamUserRepository.findByTeamIdAndYougileUserId(team.getId(), remote.getResponsible())
                    .ifPresent(tu -> {
                        if (!tu.equals(task.getAssignee())) {
                            task.setAssignee(tu);
                        }
                    });
        }

        if (changed) {
            taskRepository.save(task);
        }
*/

//        log.info("Synced task {} from YouGile (changed={})", id, changed);
        return task;
    }

    @Transactional(readOnly = true)
    public Page<Task> listByTeam(Long chatId, TaskStatus status, Pageable pageable) {
        Team team = teamRepository.findByTelegramChatId(chatId)
                .orElseThrow(() -> AppException.notFound(
                        "Team not found for chatId %d".formatted(chatId)));
        if (status != null) {
            return taskRepository.findByTeamIdAndStatus(team.getId(), status, pageable);
        }
        return taskRepository.findByTeamId(team.getId(), pageable);
    }

    @Transactional(readOnly = true)
    public Page<Task> list(Long chatId, Long assigneeTelegramId, String rawStatus, Pageable pageable) {
        List<TaskStatus> statuses = resolveStatusFilter(rawStatus);
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
                return taskRepository.findByTeamIdAndAssigneeUserTelegramIdAndStatusIn(
                        teamId,
                        assigneeTelegramId,
                        statuses,
                        pageable
                );
            }
            return taskRepository.findByTeamIdAndAssigneeUserTelegramId(teamId, assigneeTelegramId, pageable);
        }

        if (teamId != null) {
            if (statuses != null) {
                return taskRepository.findByTeamIdAndStatusIn(teamId, statuses, pageable);
            }
            return taskRepository.findByTeamId(teamId, pageable);
        }

        if (statuses != null) {
            return taskRepository.findByAssigneeUserTelegramIdAndStatusIn(assigneeTelegramId, statuses, pageable);
        }
        return taskRepository.findByAssigneeUserTelegramId(assigneeTelegramId, pageable);
    }

    @Transactional(readOnly = true)
    public List<YouGileService.YouGileTaskResponse> listFromYouGile(Long chatId) {
        Team team = teamRepository.findByTelegramChatId(chatId)
                .orElseThrow(() -> AppException.notFound(
                        "Team not found for chatId %d".formatted(chatId)));
        return youGileService.fetchAllTasksForBoard(team);
    }

/*
    private void syncToYouGile(Task task, Team team) {
        Exception lastException = null;
        for (int attempt = 1; attempt <= YOUGILE_MAX_RETRIES; attempt++) {
            try {
                Optional<String> externalId = youGileService.createTask(team, task);
                if (externalId.isPresent()) {
                    task.setExternalId(externalId.get());
                    task.setSyncStatus(TaskSyncStatus.SYNCED);
                    taskRepository.save(task);
                    taskEventPublisher.publishConfirmation(task);
                    log.info("Task {} synced to YouGile as {}", task.getId(), externalId.get());
                } else {
                    log.warn("YouGile returned empty id for task {}, marking SYNC_FAILED", task.getId());
                    task.setSyncStatus(TaskSyncStatus.SYNC_FAILED);
                    taskRepository.save(task);
                }
                return;
            } catch (Exception e) {
                lastException = e;
                log.warn("YouGile sync attempt {}/{} failed for task {}: {}",
                        attempt, YOUGILE_MAX_RETRIES, task.getId(), e.getMessage());
                if (attempt < YOUGILE_MAX_RETRIES) {
                    sleep(RETRY_BASE_MS * (1L << (attempt - 1)));
                }
            }
        }
        log.error("YouGile sync failed after {} retries for task {}. Keeping PENDING_SYNC.",
                YOUGILE_MAX_RETRIES, task.getId(), lastException);
        // Task stays PENDING_SYNC — a cron job can retry later
    }
*/

    private void validateEvent(LlmTaskCreateEvent event) {
        if (event.getChatId() == null) throw AppException.badRequest("chatId is required");
        if (event.getTitle() == null || event.getTitle().isBlank())
            throw AppException.badRequest("title is required");
    }

    private Optional<TeamUser> resolveTeamUser(Team team, Long telegramId) {
        return teamUserRepository.findByTeamIdAndUserTelegramId(team.getId(), telegramId);
    }

    private List<TaskStatus> resolveStatusFilter(String rawStatus) {
        if (rawStatus == null || rawStatus.isBlank()) {
            return null;
        }

        String normalized = rawStatus.trim().toUpperCase(Locale.ROOT);
        if ("ACTIVE".equals(normalized)) {
            return ACTIVE_STATUSES;
        }

        try {
            return List.of(TaskStatus.valueOf(normalized));
        } catch (IllegalArgumentException e) {
            throw AppException.badRequest("Unknown task status: " + rawStatus);
        }
    }

    private void recordHistory(Task task, TaskStatus from, TaskStatus to, Long telegramId) {
        TaskStatusHistory h = new TaskStatusHistory();
        h.setTask(task);
        h.setFromStatus(from);
        h.setToStatus(to);
        h.setChangedByTelegramId(telegramId);
        historyRepository.save(h);
    }

    private static void sleep(long ms) {
        try {
            Thread.sleep(ms);
        } catch (InterruptedException ie) {
            Thread.currentThread().interrupt();
        }
    }
}
