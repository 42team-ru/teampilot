package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.dto.response.TaskUpdateMessage;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.TaskColumn;
import ru.team42.monolith.entity.TaskStatusHistory;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.entity.enums.TaskLocalStatus;
import ru.team42.monolith.entity.enums.TaskSyncStatus;
import ru.team42.monolith.entity.enums.TeamRole;
import ru.team42.monolith.entity.enums.UserSyncStatus;
import ru.team42.monolith.event.BotSyncEvent;
import ru.team42.monolith.event.ChatMessageEvent;
import ru.team42.monolith.event.SyncDraftEvent;
import ru.team42.monolith.event.SyncRequestEvent;
import ru.team42.monolith.kanban.YouGileService;
import ru.team42.monolith.repository.TaskColumnRepository;
import ru.team42.monolith.repository.TaskRepository;
import ru.team42.monolith.repository.TaskStatusHistoryRepository;
import ru.team42.monolith.repository.TeamRepository;
import ru.team42.monolith.repository.TeamUserRepository;

import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class EveningSyncService {

    private static final List<String> DONE_COLUMN_TITLES = List.of(
            "готово", "done", "выполнено", "выполнена", "завершено", "завершена", "completed");

    private final SyncStateService syncStateService;
    private final SyncEventPublisher syncEventPublisher;
    private final TaskRepository taskRepository;
    private final TaskColumnRepository taskColumnRepository;
    private final TaskStatusHistoryRepository taskStatusHistoryRepository;
    private final TeamRepository teamRepository;
    private final TeamUserRepository teamUserRepository;
    private final TaskEventPublisher taskEventPublisher;
    private final YouGileService youGileService;
    private final ExcuseService excuseService;
    private final SimpMessagingTemplate messagingTemplate;

    public void startSyncForAllTeams() {
        List<Team> teams = teamRepository.findByActiveTrue();
        for (Team team : teams) {
            if (team.getTelegramChatId() == null) continue;
            try {
                startSyncForTeam(team);
            } catch (Exception e) {
                log.error("Failed to start sync for team={}: {}", team.getId(), e.getMessage());
            }
        }
    }

    private void startSyncForTeam(Team team) {
        List<TeamUser> members = teamUserRepository.findByTeamIdWithUser(team.getId());
        // Синк только для сотрудников — менеджеры отчёт не пишут, они подтверждают
        List<TeamUser> employees = members.stream()
                .filter(m -> m.getRole() != TeamRole.MANAGER
                        && m.getUser() != null && m.getUser().getTelegramId() != null)
                .toList();
        List<Long> memberIds = employees.stream()
                .map(m -> m.getUser().getTelegramId())
                .toList();
        List<String> usernames = employees.stream()
                .map(m -> {
                    var u = m.getUser();
                    String first = u.getFirstName() != null ? u.getFirstName().trim() : "";
                    String last = u.getLastName() != null ? u.getLastName().trim() : "";
                    String name = (first + " " + last).trim();
                    if (name.isEmpty()) {
                        name = u.getTelegramLogin() != null ? u.getTelegramLogin() : u.getTelegramId().toString();
                    }
                    return name;
                })
                .toList();

        // Excused users still get a session entry (so they show up in reports), but are
        // marked EXCUSED from the start and don't receive the sync prompt
        Set<Long> excusedIds = memberIds.stream()
                .filter(id -> excuseService.isExcused(id, team.getId()))
                .collect(Collectors.toSet());

        syncStateService.openSession(team.getId(), team.getTelegramChatId(), memberIds, usernames, excusedIds);

        List<Long> promptRecipients = memberIds.stream()
                .filter(id -> !excusedIds.contains(id))
                .toList();
        syncEventPublisher.publishSyncPrompt(team.getTelegramChatId(), promptRecipients);
        log.info("Evening sync started for team={} chatId={}", team.getId(), team.getTelegramChatId());
    }

    @Transactional(readOnly = true)
    public void handleSyncMessage(ChatMessageEvent event, UUID teamId) {
        handleSyncMessage(event.getUserId(), event.getText(), teamId);
    }

    @Transactional(readOnly = true)
    public void handleSyncMessage(Long telegramUserId, String text, UUID teamId) {
        String requestId = UUID.randomUUID().toString();

        List<Task> activeTasks = taskRepository
                .findByAssigneeUserTelegramIdAndCompletedFalseAndDeletedFalseAndLocalStatus(
                        telegramUserId, TaskLocalStatus.ACTIVE);

        List<SyncRequestEvent.TaskSummary> summaries = activeTasks.stream()
                .map(t -> SyncRequestEvent.TaskSummary.builder()
                        .id(t.getId().toString())
                        .title(t.getTitle())
                        .description(t.getDescription())
                        .build())
                .toList();

        Long chatId = syncStateService.getSession(teamId)
                .map(SyncStateService.TeamSyncSession::chatId)
                .orElse(null);

        syncStateService.recordUserResponse(teamId, telegramUserId, text, requestId);

        syncEventPublisher.publishSyncRequest(SyncRequestEvent.builder()
                .requestId(requestId)
                .teamId(teamId.toString())
                .chatId(chatId)
                .telegramUserId(telegramUserId)
                .username(null)
                .rawText(text)
                .activeTasks(summaries)
                .build());

        log.info("Sync request dispatched for user={} team={} requestId={}", telegramUserId, teamId, requestId);
    }

    @Transactional
    public void handleDraft(SyncDraftEvent event) {
        UUID teamId;
        try {
            teamId = UUID.fromString(event.getTeamId());
        } catch (IllegalArgumentException e) {
            log.warn("Invalid teamId in SyncDraftEvent: {}", event.getTeamId());
            return;
        }

        Team team = teamRepository.findById(teamId).orElse(null);
        if (team == null) {
            log.warn("handleDraft: team not found for teamId={}", teamId);
            return;
        }

        List<SyncDraftEvent.DraftItem> items = event.getItems() == null ? List.of() : event.getItems();

        List<String> confirmedTitles = new ArrayList<>();
        List<String> pendingTitles = new ArrayList<>();
        for (SyncDraftEvent.DraftItem item : items) {
            try {
                if (item.isNewTask()) {
                    createCompletedTask(team, item.getTaskTitle(), event.getTelegramUserId());
                    pendingTitles.add(resolveTaskTitle(item));
                } else if (item.getTaskId() != null) {
                    markTaskComplete(team, item.getTaskId());
                    confirmedTitles.add(resolveTaskTitle(item));
                }
            } catch (Exception e) {
                log.error("Failed to process sync item '{}' for user={}: {}", item.getUserText(), event.getTelegramUserId(), e.getMessage());
            }
        }

        syncStateService.recordSyncResults(teamId, event.getTelegramUserId(), confirmedTitles, pendingTitles);
        log.info("Sync draft auto-applied for user={} team={} confirmed={} pending={}",
                event.getTelegramUserId(), teamId, confirmedTitles.size(), pendingTitles.size());
    }

    public void closeSyncAndSendSummary() {
        List<SyncStateService.TeamSyncSession> snapshot = List.copyOf(syncStateService.getAllSessions());
        for (SyncStateService.TeamSyncSession session : snapshot) {
            try {
                sendSummaryForTeam(session);
            } catch (Exception e) {
                log.error("Failed to send summary for team={}: {}", session.teamId(), e.getMessage());
            } finally {
                syncStateService.closeSession(session.teamId());
            }
        }
    }

    private void sendSummaryForTeam(SyncStateService.TeamSyncSession session) {
        List<String> responded = new ArrayList<>();
        List<String> notResponded = new ArrayList<>();
        int confirmed = 0;
        int pending = 0;

        for (SyncStateService.UserSyncState u : session.userStates().values()) {
            // EXCUSED users are reported in the dedicated excused block — skip them here
            if (u.status() == UserSyncStatus.EXCUSED) {
                continue;
            }
            if (u.status() == UserSyncStatus.AWAITING
                    && u.confirmedTasksCount() == 0 && u.pendingTasksCount() == 0) {
                notResponded.add(u.username());
            } else {
                responded.add(u.username());
            }
            confirmed += u.confirmedTasksCount();
            pending += u.pendingTasksCount();
        }

        // Load all members once for both excused lookup and manager filtering
        List<TeamUser> allMembers = teamUserRepository.findByTeamIdWithUser(session.teamId());

        // Build excused users info from ExcuseService
        Map<Long, String> excusedMap = excuseService.getExcusedForTeam(session.teamId());

        // Build per-member summary (one entry per team member in the session)
        List<BotSyncEvent.SyncSummary.MemberSummary> members = new ArrayList<>();
        for (SyncStateService.UserSyncState u : session.userStates().values()) {
            UserSyncStatus status = u.status();
            String excuseReason = excusedMap.get(u.telegramId());
            if (excuseReason != null) {
                status = UserSyncStatus.EXCUSED;
            }
            members.add(BotSyncEvent.SyncSummary.MemberSummary.builder()
                    .telegramId(u.telegramId())
                    .username(u.username())
                    .status(status.name())
                    .excuseReason(excuseReason)
                    .confirmedTasks(u.confirmedTaskTitles())
                    .pendingTasks(u.pendingTaskTitles())
                    .rawText(u.rawText())
                    .build());
        }

        List<String> excusedEntries = new ArrayList<>();
        if (!excusedMap.isEmpty()) {
            Map<Long, String> telegramIdToName = new HashMap<>();
            for (TeamUser m : allMembers) {
                if (m.getUser() != null && m.getUser().getTelegramId() != null) {
                    var u = m.getUser();
                    String first = u.getFirstName() != null ? u.getFirstName().trim() : "";
                    String last = u.getLastName() != null ? u.getLastName().trim() : "";
                    String name = (first + " " + last).trim();
                    if (name.isEmpty()) {
                        name = u.getTelegramLogin() != null ? u.getTelegramLogin() : u.getTelegramId().toString();
                    }
                    telegramIdToName.put(u.getTelegramId(), name);
                }
            }
            for (Map.Entry<Long, String> entry : excusedMap.entrySet()) {
                String name = telegramIdToName.getOrDefault(entry.getKey(), entry.getKey().toString());
                excusedEntries.add(name + " — " + entry.getValue());
            }
        }

        List<TeamUser> managers = allMembers.stream()
                .filter(m -> m.getRole() == TeamRole.MANAGER && m.getUser() != null && m.getUser().getTelegramId() != null)
                .toList();

        excuseService.persistSickLeaveHistory(session.teamId(), excusedMap);

        if (managers.isEmpty()) {
            log.warn("No managers found for team={}", session.teamId());
            excuseService.clearTeam(session.teamId());
            return;
        }

        List<Long> managerIds = managers.stream().map(m -> m.getUser().getTelegramId()).toList();
        syncEventPublisher.publishSyncSummary(managerIds, session.teamId(), responded, notResponded, confirmed, pending, excusedEntries, members);
        excuseService.clearTeam(session.teamId());
    }

    @Transactional
    public void approveTask(String taskId, Long telegramUserId) {
        UUID id;
        try {
            id = UUID.fromString(taskId);
        } catch (IllegalArgumentException e) {
            throw AppException.badRequest("Invalid taskId: " + taskId);
        }
        Task task = taskRepository.findById(id)
                .orElseThrow(() -> AppException.notFound("Task %s not found".formatted(taskId)));
        teamUserRepository.findByTeamIdAndUserTelegramId(task.getTeam().getId(), telegramUserId)
                .filter(m -> m.getRole() == TeamRole.MANAGER)
                .orElseThrow(() -> AppException.forbidden("Only managers can approve tasks"));
        if (task.getLocalStatus() != TaskLocalStatus.PENDING_APPROVAL) {
            throw AppException.badRequest("Task is not pending approval");
        }
        task.setCompleted(true);
        task.setLocalStatus(TaskLocalStatus.ACTIVE);
        Task saved = taskRepository.save(task);
        youGileService.createTask(saved.getTeam(), saved).ifPresent(externalId -> {
            saved.setExternalId(externalId);
            saved.setSyncStatus(TaskSyncStatus.SYNCED);
            taskRepository.save(saved);
        });
        taskEventPublisher.publishCreated(saved);
        broadcastTaskUpdate(saved, TaskUpdateMessage.approved(saved.getId(), saved.getTitle(), resolveActorName(saved.getTeam().getId(), telegramUserId)));
        log.info("Task '{}' approved by manager telegramId={}", task.getTitle(), telegramUserId);
    }

    @Transactional
    public void rejectTask(String taskId, Long telegramUserId) {
        UUID id;
        try {
            id = UUID.fromString(taskId);
        } catch (IllegalArgumentException e) {
            throw AppException.badRequest("Invalid taskId: " + taskId);
        }
        Task task = taskRepository.findById(id)
                .orElseThrow(() -> AppException.notFound("Task %s not found".formatted(taskId)));
        teamUserRepository.findByTeamIdAndUserTelegramId(task.getTeam().getId(), telegramUserId)
                .filter(m -> m.getRole() == TeamRole.MANAGER)
                .orElseThrow(() -> AppException.forbidden("Only managers can reject tasks"));
        task.setDeleted(true);
        taskRepository.save(task);
        taskEventPublisher.publishCancelled(task);
        broadcastTaskUpdate(task, TaskUpdateMessage.rejected(task.getId(), task.getTitle(), resolveActorName(task.getTeam().getId(), telegramUserId)));
        log.info("Task '{}' rejected by manager telegramId={}", task.getTitle(), telegramUserId);
    }

    private void createCompletedTask(Team team, String title, Long reporterTelegramId) {
        Task task = new Task();
        task.setTeam(team);
        task.setTitle(title);
        task.setCompleted(true);
        task.setLocalStatus(TaskLocalStatus.ACTIVE);
        task.setSyncStatus(TaskSyncStatus.PENDING_SYNC);
        resolveDoneColumn(team).ifPresent(task::setColumn);
        teamUserRepository.findByTeamIdAndUserTelegramId(team.getId(), reporterTelegramId)
                .ifPresent(task::setAssignee);

        Task saved = taskRepository.save(task);
        youGileService.createTask(team, saved).ifPresent(externalId -> {
            saved.setExternalId(externalId);
            saved.setSyncStatus(TaskSyncStatus.SYNCED);
            taskRepository.save(saved);
        });
        taskEventPublisher.publishCreated(saved);
        log.info("New task '{}' auto-created from sync for team={}, reporter telegramId={}, taskId={}",
                title, team.getId(), reporterTelegramId, saved.getId());
    }

    private String resolveTaskTitle(SyncDraftEvent.DraftItem item) {
        if (item.getTaskTitle() != null && !item.getTaskTitle().isBlank()) {
            return item.getTaskTitle();
        }
        if (item.getTaskId() == null) {
            return item.getUserText();
        }
        try {
            UUID taskId = UUID.fromString(item.getTaskId());
            return taskRepository.findById(taskId).map(Task::getTitle).orElse(item.getUserText());
        } catch (IllegalArgumentException e) {
            return item.getUserText();
        }
    }

    private void markTaskComplete(Team team, String taskIdStr) {
        UUID taskId;
        try {
            taskId = UUID.fromString(taskIdStr);
        } catch (IllegalArgumentException e) {
            log.warn("Invalid taskId '{}' in sync draft", taskIdStr);
            return;
        }

        taskRepository.findById(taskId).ifPresent(task -> {
            task.setCompleted(true);
            resolveDoneColumn(team)
                    .filter(col -> !col.equals(task.getColumn()))
                    .ifPresent(col -> {
                        TaskColumn prev = task.getColumn();
                        task.setColumn(col);
                        recordHistory(task, prev, col);
                        taskEventPublisher.publishColumnChanged(task, col);
                    });
            taskRepository.save(task);
            youGileService.updateTask(team, task);
            log.info("Task '{}' marked complete via sync", task.getTitle());
        });
    }

    private void recordHistory(Task task, TaskColumn from, TaskColumn to) {
        TaskStatusHistory history = new TaskStatusHistory();
        history.setTask(task);
        history.setFromColumn(from);
        history.setToColumn(to);
        history.setChangedByTelegramId(telegramIdOf(task));
        taskStatusHistoryRepository.save(history);
    }

    private Long telegramIdOf(Task task) {
        return task.getAssignee() != null && task.getAssignee().getUser() != null
                ? task.getAssignee().getUser().getTelegramId()
                : null;
    }

    /** Находит колонку команды, соответствующую статусу "выполнено", иначе — первую доступную колонку */
    private Optional<TaskColumn> resolveDoneColumn(Team team) {
        List<TaskColumn> columns = taskColumnRepository.findByTeamIdAndDeletedFalse(team.getId());
        return columns.stream()
                .filter(c -> c.getTitle() != null
                        && DONE_COLUMN_TITLES.contains(c.getTitle().trim().toLowerCase(Locale.ROOT)))
                .findFirst()
                .or(() -> columns.stream().findFirst());
    }

    private void broadcastTaskUpdate(Task task, TaskUpdateMessage message) {
        String destination = "/topic/teams/%s/task-updates".formatted(task.getTeam().getId());
        messagingTemplate.convertAndSend(destination, message);
    }

    private String resolveActorName(UUID teamId, Long telegramUserId) {
        return teamUserRepository.findByTeamIdAndUserTelegramId(teamId, telegramUserId)
                .map(m -> {
                    var u = m.getUser();
                    if (u == null) return null;
                    String first = u.getFirstName() != null ? u.getFirstName().trim() : "";
                    String last = u.getLastName() != null ? u.getLastName().trim() : "";
                    String name = (first + " " + last).trim();
                    return name.isEmpty() ? (u.getTelegramLogin() != null ? u.getTelegramLogin() : null) : name;
                })
                .orElse(null);
    }
}
