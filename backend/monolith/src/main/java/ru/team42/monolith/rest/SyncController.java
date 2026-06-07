package ru.team42.monolith.rest;

import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.entity.enums.UserSyncStatus;
import ru.team42.monolith.service.EveningSyncService;
import ru.team42.monolith.service.ExcuseService;
import ru.team42.monolith.service.SyncStateService;
import ru.team42.monolith.repository.TeamUserRepository;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/sync")
@RequiredArgsConstructor
public class SyncController {

    private final EveningSyncService eveningSyncService;
    private final SyncStateService syncStateService;
    private final ExcuseService excuseService;
    private final TeamUserRepository teamUserRepository;

    /**
     * Бот вызывает этот endpoint когда пользователь нажимает кнопки в вечернем синке.
     *
     * action:
     *   CONFIRM_ALL — подтвердить все задачи из черновика
     *   REJECT      — отклонить синк
     *   EDIT_ITEM   — отредактировать одну задачу (нужны itemIndex + newTaskTitle)
     */
    @PostMapping("/confirm")
    public ResponseEntity<?> confirm(@RequestBody SyncConfirmRequest request) {
        return switch (request.action()) {
            case "CONFIRM_ALL" -> {
                eveningSyncService.confirmAll(request.chatId(), request.telegramUserId());
                yield ResponseUtils.noContent();
            }
            case "REJECT" -> {
                eveningSyncService.rejectSync(request.chatId(), request.telegramUserId());
                yield ResponseUtils.noContent();
            }
            case "EDIT_ITEM" -> {
                eveningSyncService.editSyncItem(
                        request.chatId(), request.telegramUserId(),
                        request.itemIndex(), request.newTaskTitle());
                yield ResponseUtils.noContent();
            }
            case "COMPLETE_TASK" -> {
                eveningSyncService.completeSingleTask(request.chatId(), request.telegramUserId(), request.taskId());
                yield ResponseUtils.noContent();
            }
            case "CREATE_NEW" -> {
                eveningSyncService.createNewTaskFromSync(request.chatId(), request.telegramUserId(), request.newTaskTitle());
                yield ResponseUtils.noContent();
            }
            default -> throw AppException.badRequest("Unknown sync action: " + request.action());
        };
    }

    @PostMapping("/submit")
    @PreAuthorize("hasRole('BOT') or hasRole('SYSTEM_ADMIN')")
    public ResponseEntity<?> submit(@RequestBody SyncSubmitRequest request) {
        java.util.UUID teamId = syncStateService.getTeamIdByUserId(request.telegramUserId())
                .orElseThrow(() -> AppException.badRequest("No active sync session for user"));
        eveningSyncService.handleSyncMessage(request.telegramUserId(), request.text(), teamId);
        return ResponseUtils.noContent();
    }

    @GetMapping("/active-tasks")
    public ResponseEntity<?> getActiveTasks(@RequestParam Long telegramUserId) {
        return ResponseUtils.ok(eveningSyncService.getActiveTasks(telegramUserId));
    }

    @PostMapping("/approve-task")
    public ResponseEntity<?> approveTask(@RequestBody TaskActionRequest request) {
        eveningSyncService.approveTask(request.taskId(), request.telegramUserId());
        return ResponseUtils.noContent();
    }

    @PostMapping("/reject-task")
    public ResponseEntity<?> rejectTask(@RequestBody TaskActionRequest request) {
        eveningSyncService.rejectTask(request.taskId(), request.telegramUserId());
        return ResponseUtils.noContent();
    }

    @PostMapping("/approve-proposal")
    public ResponseEntity<?> approveProposal(@RequestBody ProposalActionRequest request) {
        eveningSyncService.approveProposal(request.proposalId(), request.telegramUserId());
        return ResponseUtils.noContent();
    }

    @PostMapping("/reject-proposal")
    public ResponseEntity<?> rejectProposal(@RequestBody ProposalActionRequest request) {
        eveningSyncService.rejectProposal(request.proposalId(), request.telegramUserId());
        return ResponseUtils.noContent();
    }

    /** Ручной триггер для тестирования — запускает вечерний синк прямо сейчас */
    @PostMapping("/trigger")
    public ResponseEntity<?> triggerSync() {
        eveningSyncService.startSyncForAllTeams();
        return ResponseUtils.noContent();
    }

    /** Ручной триггер из Telegram — запускает вечерний синк только для одного чата */
    @PostMapping("/trigger-chat")
    @PreAuthorize("hasRole('BOT') or hasRole('SYSTEM_ADMIN')")
    public ResponseEntity<?> triggerSyncForChat(@RequestBody SyncChatRequest request) {
        eveningSyncService.startSyncForChat(request.chatId(), request.telegramUserId());
        return ResponseUtils.noContent();
    }

    /** Ручной триггер закрытия окна — отправляет summary прямо сейчас */
    @PostMapping("/trigger-summary")
    public ResponseEntity<?> triggerSummary() {
        eveningSyncService.closeSyncAndSendSummary();
        return ResponseUtils.noContent();
    }

    /** Ручной триггер из Telegram — закрывает sync-окно только для одного чата */
    @PostMapping("/trigger-summary-chat")
    @PreAuthorize("hasRole('BOT') or hasRole('SYSTEM_ADMIN')")
    public ResponseEntity<?> triggerSummaryForChat(@RequestBody SyncChatRequest request) {
        eveningSyncService.closeSyncAndSendSummaryForChat(request.chatId(), request.telegramUserId());
        return ResponseUtils.noContent();
    }

    /** Возвращает список команд пользователя для выбора при /excuse */
    @GetMapping("/excuse/teams")
    @Transactional(readOnly = true)
    public ResponseEntity<?> getExcuseTeams(@RequestParam Long telegramUserId) {
        List<Map<String, String>> teams = teamUserRepository.findAllByUserTelegramIdWithTeam(telegramUserId)
                .stream()
                .map(tu -> {
                    String name = tu.getTeam().getChatTitle() != null
                            ? tu.getTeam().getChatTitle()
                            : tu.getTeam().getId().toString();
                    return Map.of("teamId", tu.getTeam().getId().toString(), "teamName", name);
                })
                .toList();
        return ResponseUtils.ok(teams);
    }

    /** Пользователь отписывается от вечернего синка для одной или всех команд */
    @PostMapping("/excuse")
    @Transactional(readOnly = true)
    public ResponseEntity<?> excuse(@RequestBody ExcuseRequest request) {
        if (request.teamId() != null) {
            excuseService.excuse(request.telegramUserId(), request.teamId(), request.reason());
            // If sync is currently active for this team, mark the user as EXCUSED
            syncStateService.getSession(request.teamId()).ifPresent(session -> {
                if (session.userStates().containsKey(request.telegramUserId())) {
                    syncStateService.updateUserStatus(request.teamId(), request.telegramUserId(),
                            UserSyncStatus.EXCUSED);
                }
            });
        } else {
            // excuse from all teams
            List<UUID> teamIds = teamUserRepository.findAllByUserTelegramIdWithTeam(request.telegramUserId())
                    .stream()
                    .map(tu -> tu.getTeam().getId())
                    .toList();
            excuseService.excuseAllTeams(request.telegramUserId(), teamIds, request.reason());
            // Mark user EXCUSED in all active sessions
            for (UUID teamId : teamIds) {
                syncStateService.getSession(teamId).ifPresent(session -> {
                    if (session.userStates().containsKey(request.telegramUserId())) {
                        syncStateService.updateUserStatus(teamId, request.telegramUserId(),
                                UserSyncStatus.EXCUSED);
                    }
                });
            }
        }
        return ResponseUtils.noContent();
    }

    public record SyncConfirmRequest(
            Long chatId,
            Long telegramUserId,
            String action,
            int itemIndex,
            String newTaskTitle,
            String taskId
    ) {}

    public record SyncSubmitRequest(
            Long telegramUserId,
            String text
    ) {}

    public record SyncChatRequest(
            Long chatId,
            Long telegramUserId
    ) {}

    public record TaskActionRequest(
            String taskId,
            Long telegramUserId
    ) {}

    public record ProposalActionRequest(
            String proposalId,
            Long telegramUserId
    ) {}

    public record ExcuseRequest(
            Long telegramUserId,
            UUID teamId,
            String reason
    ) {}
}
