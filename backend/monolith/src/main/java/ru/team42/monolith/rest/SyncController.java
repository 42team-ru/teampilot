package ru.team42.monolith.rest;

import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.service.EveningSyncService;
import ru.team42.monolith.service.SyncStateService;

@RestController
@RequestMapping("/sync")
@RequiredArgsConstructor
public class SyncController {

    private final EveningSyncService eveningSyncService;
    private final SyncStateService syncStateService;

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

    /** Ручной триггер закрытия окна — отправляет summary прямо сейчас */
    @PostMapping("/trigger-summary")
    public ResponseEntity<?> triggerSummary() {
        eveningSyncService.closeSyncAndSendSummary();
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

    public record TaskActionRequest(
            String taskId,
            Long telegramUserId
    ) {}

    public record ProposalActionRequest(
            String proposalId,
            Long telegramUserId
    ) {}
}
