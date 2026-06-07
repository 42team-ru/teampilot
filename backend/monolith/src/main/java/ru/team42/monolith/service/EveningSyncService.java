package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.entity.enums.TaskLocalStatus;
import ru.team42.monolith.entity.enums.TaskSyncStatus;
import ru.team42.monolith.entity.enums.TeamRole;
import ru.team42.monolith.event.ChatMessageEvent;
import ru.team42.monolith.event.SyncDraftEvent;
import ru.team42.monolith.event.SyncRequestEvent;
import ru.team42.monolith.kanban.YouGileService;
import ru.team42.monolith.repository.TaskRepository;
import ru.team42.monolith.repository.TeamRepository;
import ru.team42.monolith.repository.TeamUserRepository;

import java.util.*;

@Slf4j
@Service
@RequiredArgsConstructor
public class EveningSyncService {

    private final SyncStateService syncStateService;
    private final SyncEventPublisher syncEventPublisher;
    private final TaskRepository taskRepository;
    private final TeamRepository teamRepository;
    private final TeamUserRepository teamUserRepository;
    private final TaskEventPublisher taskEventPublisher;
    private final YouGileService youGileService;
    private final TaskProposalCache proposalCache;

    @Transactional(readOnly = true)
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

        syncStateService.openSession(team.getId(), team.getTelegramChatId(), memberIds, usernames);
        syncEventPublisher.publishSyncPrompt(team.getTelegramChatId(), memberIds);
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

    @Transactional(readOnly = true)
    public void handleDraft(SyncDraftEvent event) {
        UUID teamId;
        try {
            teamId = UUID.fromString(event.getTeamId());
        } catch (IllegalArgumentException e) {
            log.warn("Invalid teamId in SyncDraftEvent: {}", event.getTeamId());
            return;
        }

        Long chatId = syncStateService.getSession(teamId)
                .map(SyncStateService.TeamSyncSession::chatId)
                .orElse(null);
        if (chatId == null) {
            chatId = teamRepository.findById(teamId)
                    .map(Team::getTelegramChatId)
                    .orElse(null);
            if (chatId != null) {
                log.info("handleDraft: using DB chatId={} for teamId={} (no active session)", chatId, teamId);
            } else {
                log.warn("handleDraft: no chatId found for teamId={} - draft may not be delivered", teamId);
            }
        }

        List<SyncDraftEvent.DraftItem> enrichedItems = event.getItems() == null ? List.of() :
            event.getItems().stream().map(item -> {
                if (item.getTaskId() == null || item.isNewTask()) return item;
                try {
                    return taskRepository.findById(UUID.fromString(item.getTaskId()))
                        .map(task -> {
                            Long assigneeId = Optional.ofNullable(task.getAssignee())
                                    .map(tu -> tu.getUser())
                                    .map(u -> u.getTelegramId())
                                    .orElse(null);
                            String assigneeName = Optional.ofNullable(task.getAssignee())
                                    .map(tu -> tu.getUser())
                                    .map(u -> (u.getFirstName() != null ? u.getFirstName() : "") +
                                             (u.getLastName() != null ? " " + u.getLastName() : ""))
                                    .map(String::trim)
                                    .filter(s -> !s.isEmpty())
                                    .orElse(null);
                            return SyncDraftEvent.DraftItem.builder()
                                    .index(item.getIndex())
                                    .userText(item.getUserText())
                                    .taskId(item.getTaskId())
                                    .taskTitle(item.getTaskTitle())
                                    .isNewTask(item.isNewTask())
                                    .assigneeTelegramId(assigneeId)
                                    .assigneeName(assigneeName)
                                    .build();
                        })
                        .orElse(item);
                } catch (Exception e) {
                    return item;
                }
            }).toList();

        log.info("handleDraft: publishing draft to user={} chatId={} items={}", event.getTelegramUserId(), chatId, enrichedItems.size());
        syncStateService.storeDraft(teamId, event.getRequestId(), enrichedItems);
        syncEventPublisher.publishDraftToUser(event.getTelegramUserId(), chatId, enrichedItems);
    }

    @Transactional
    public void confirmAll(Long chatId, Long telegramUserId) {
        UUID teamId = syncStateService.getTeamIdByChatId(chatId)
                .orElseThrow(() -> AppException.badRequest("No active sync session for chat"));

        SyncStateService.UserSyncState state = syncStateService.getUserState(teamId, telegramUserId)
                .orElseThrow(() -> AppException.notFound("User not in sync session"));

        if (state.status() != SyncStateService.UserSyncStatus.DRAFT_SENT) {
            throw AppException.badRequest("No draft pending for user");
        }

        Team team = teamRepository.findById(teamId)
                .orElseThrow(() -> AppException.notFound("Team not found"));

        int confirmedCount = 0;
        int pendingCount = 0;
        for (SyncDraftEvent.DraftItem item : state.draft()) {
            try {
                if (item.isNewTask()) {
                    createCompletedTaskPendingApproval(team, item.getTaskTitle(), telegramUserId);
                    pendingCount++;
                } else if (item.getTaskId() != null) {
                    markTaskComplete(team, item.getTaskId());
                    confirmedCount++;
                }
            } catch (Exception e) {
                log.error("Failed to process sync item '{}' for user={}: {}", item.getUserText(), telegramUserId, e.getMessage());
            }
        }

        syncStateService.addConfirmCounts(teamId, telegramUserId, confirmedCount, pendingCount);
        log.info("User={} confirmed sync for team={} confirmed={} pending={}", telegramUserId, teamId, confirmedCount, pendingCount);
    }

    @Transactional
    public void rejectSync(Long chatId, Long telegramUserId) {
        syncStateService.getTeamIdByChatId(chatId).ifPresent(teamId ->
                syncStateService.updateUserStatus(teamId, telegramUserId, SyncStateService.UserSyncStatus.REJECTED));
        log.info("User={} rejected sync for chatId={}", telegramUserId, chatId);
    }

    @Transactional
    public void editSyncItem(Long chatId, Long telegramUserId, int itemIndex, String newTaskTitle) {
        UUID teamId = syncStateService.getTeamIdByChatId(chatId)
                .orElseThrow(() -> AppException.badRequest("No active sync session for chat"));

        SyncStateService.UserSyncState state = syncStateService.getUserState(teamId, telegramUserId)
                .orElseThrow(() -> AppException.notFound("User not in sync session"));

        List<SyncDraftEvent.DraftItem> updated = state.draft().stream()
                .map(item -> item.getIndex() == itemIndex
                        ? SyncDraftEvent.DraftItem.builder()
                                .index(item.getIndex())
                                .userText(item.getUserText())
                                .taskId(null)
                                .taskTitle(newTaskTitle)
                                .isNewTask(true)
                                .build()
                        : item)
                .toList();

        syncStateService.storeDraft(teamId, state.requestId(), updated);
        syncEventPublisher.publishDraftToUser(telegramUserId, chatId, updated);
    }

    @Transactional(readOnly = true)
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
            if (u.status() == SyncStateService.UserSyncStatus.AWAITING
                    && u.confirmedTasksCount() == 0 && u.pendingTasksCount() == 0) {
                notResponded.add(u.username());
            } else {
                responded.add(u.username());
            }
            confirmed += u.confirmedTasksCount();
            pending += u.pendingTasksCount();
        }

        List<TeamUser> managers = teamUserRepository.findByTeamIdWithUser(session.teamId()).stream()
                .filter(m -> m.getRole() == TeamRole.MANAGER && m.getUser() != null && m.getUser().getTelegramId() != null)
                .toList();

        if (managers.isEmpty()) {
            log.warn("No managers found for team={}", session.teamId());
            return;
        }

        List<Long> managerIds = managers.stream().map(m -> m.getUser().getTelegramId()).toList();
        syncEventPublisher.publishSyncSummary(managerIds, session.teamId(), responded, notResponded, confirmed, pending);
    }

    @Transactional
    public void createNewTaskFromSync(Long chatId, Long telegramUserId, String title) {
        if (title == null || title.isBlank()) throw AppException.badRequest("Task title is required");
        Team team = syncStateService.getTeamIdByChatId(chatId)
                .flatMap(teamRepository::findById)
                .or(() -> teamRepository.findByTelegramChatIdAndActiveTrue(chatId))
                .orElseThrow(() -> AppException.notFound("No team found for chat"));
        createCompletedTaskPendingApproval(team, title, telegramUserId);
    }

    @Transactional(readOnly = true)
    public List<java.util.Map<String, String>> getActiveTasks(Long telegramUserId) {
        return taskRepository
                .findByAssigneeUserTelegramIdAndCompletedFalseAndDeletedFalseAndLocalStatus(
                        telegramUserId, TaskLocalStatus.ACTIVE)
                .stream()
                .map(t -> java.util.Map.of("id", t.getId().toString(), "title", t.getTitle()))
                .toList();
    }

    @Transactional
    public void completeSingleTask(Long chatId, Long telegramUserId, String taskId) {
        if (taskId == null || taskId.isBlank()) throw AppException.badRequest("taskId is required");
        UUID id;
        try {
            id = UUID.fromString(taskId);
        } catch (IllegalArgumentException e) {
            throw AppException.badRequest("Invalid taskId: " + taskId);
        }
        taskRepository.findById(id).ifPresent(task -> {
            task.setCompleted(true);
            taskRepository.save(task);
            youGileService.updateTask(task.getTeam(), task);
            log.info("Task '{}' marked complete via sync pick by user={}", task.getTitle(), telegramUserId);
        });
        syncStateService.getTeamIdByChatId(chatId)
                .ifPresent(teamId -> syncStateService.addConfirmCounts(teamId, telegramUserId, 1, 0));
    }

    @Transactional
    public void approveProposal(String proposalId, Long telegramUserId) {
        TaskProposalCache.PendingProposal proposal = proposalCache.get(proposalId)
                .orElseThrow(() -> AppException.notFound("Proposal not found or already processed"));
        teamUserRepository.findByTeamIdAndUserTelegramId(proposal.teamId(), telegramUserId)
                .filter(m -> m.getRole() == TeamRole.MANAGER)
                .orElseThrow(() -> AppException.forbidden("Only managers can approve proposals"));

        Team team = teamRepository.findById(proposal.teamId())
                .orElseThrow(() -> AppException.notFound("Team not found"));

        Task task = new Task();
        task.setTeam(team);
        task.setTitle(proposal.title());
        task.setCompleted(true);
        task.setLocalStatus(TaskLocalStatus.ACTIVE);
        task.setSyncStatus(TaskSyncStatus.PENDING_SYNC);
        teamUserRepository.findByTeamIdAndUserTelegramId(team.getId(), proposal.reporterTelegramId())
                .ifPresent(task::setAssignee);

        Task saved = taskRepository.save(task);
        youGileService.createTask(team, saved).ifPresent(externalId -> {
            saved.setExternalId(externalId);
            saved.setSyncStatus(TaskSyncStatus.SYNCED);
            taskRepository.save(saved);
        });
        taskEventPublisher.publishCreated(saved);
        proposalCache.remove(proposalId);
        log.info("Proposal '{}' approved by manager telegramId={}, task created id={}", proposal.title(), telegramUserId, saved.getId());
    }

    public void rejectProposal(String proposalId, Long telegramUserId) {
        TaskProposalCache.PendingProposal proposal = proposalCache.get(proposalId)
                .orElseThrow(() -> AppException.notFound("Proposal not found or already processed"));
        teamUserRepository.findByTeamIdAndUserTelegramId(proposal.teamId(), telegramUserId)
                .filter(m -> m.getRole() == TeamRole.MANAGER)
                .orElseThrow(() -> AppException.forbidden("Only managers can reject proposals"));
        proposalCache.remove(proposalId);
        log.info("Proposal '{}' rejected by manager telegramId={}", proposal.title(), telegramUserId);
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
        log.info("Task '{}' rejected by manager telegramId={}", task.getTitle(), telegramUserId);
    }

    private void createCompletedTaskPendingApproval(Team team, String title, Long reporterTelegramId) {
        String reporterName = teamUserRepository.findByTeamIdAndUserTelegramId(team.getId(), reporterTelegramId)
                .map(m -> {
                    var u = m.getUser();
                    if (u == null) return null;
                    String first = u.getFirstName() != null ? u.getFirstName().trim() : "";
                    String last = u.getLastName() != null ? u.getLastName().trim() : "";
                    String name = (first + " " + last).trim();
                    return name.isEmpty() ? (u.getTelegramLogin() != null ? u.getTelegramLogin() : u.getTelegramId().toString()) : name;
                })
                .orElse("Сотрудник");

        String proposalId = proposalCache.put(new TaskProposalCache.PendingProposal(title, reporterTelegramId, team.getId()));
        taskEventPublisher.publishProposal(proposalId, team.getId(), title, reporterName);
        log.info("New task proposal '{}' stored as proposalId={} for team={}", title, proposalId, team.getId());
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
            taskRepository.save(task);
            youGileService.updateTask(team, task);
            log.info("Task '{}' marked complete via sync", task.getTitle());
        });
    }
}
