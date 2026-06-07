package ru.team42.monolith.rest;

import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.service.NotificationSettingsService;
import ru.team42.monolith.service.NotificationSettingsService.ReminderSettingsUpdate;

@RestController
@RequestMapping("/notifications")
@RequiredArgsConstructor
public class NotificationSettingsController {

    private final NotificationSettingsService notificationSettingsService;

    @GetMapping("/settings")
    @PreAuthorize("hasRole('BOT') or hasRole('SYSTEM_ADMIN')")
    public ResponseEntity<ReminderSettingsResponse> getSettings(
            @RequestParam Long chatId,
            @RequestParam Long telegramUserId
    ) {
        return ResponseUtils.ok(toResponse(notificationSettingsService.getSettings(chatId, telegramUserId)));
    }

    @PatchMapping("/settings")
    @PreAuthorize("hasRole('BOT') or hasRole('SYSTEM_ADMIN')")
    public ResponseEntity<ReminderSettingsResponse> updateSettings(@RequestBody ReminderSettingsRequest request) {
        Team team = notificationSettingsService.updateSettings(
                request.chatId(),
                request.telegramUserId(),
                new ReminderSettingsUpdate(
                        request.maxRemindersPerTaskPerDay(),
                        request.quietHoursStart(),
                        request.quietHoursEnd(),
                        request.staleReminderHours(),
                        request.deadlineReminderMinutesBefore()
                )
        );
        return ResponseUtils.ok(toResponse(team));
    }

    private ReminderSettingsResponse toResponse(Team team) {
        return new ReminderSettingsResponse(
                team.getTelegramChatId(),
                team.getReminderMaxPerTaskPerDay(),
                team.getReminderQuietHoursStart(),
                team.getReminderQuietHoursEnd(),
                team.getStaleReminderHours(),
                team.getDeadlineReminderMinutesBefore()
        );
    }

    public record ReminderSettingsRequest(
            Long chatId,
            Long telegramUserId,
            Integer maxRemindersPerTaskPerDay,
            Integer quietHoursStart,
            Integer quietHoursEnd,
            Integer staleReminderHours,
            Integer deadlineReminderMinutesBefore
    ) {}

    public record ReminderSettingsResponse(
            Long chatId,
            int maxRemindersPerTaskPerDay,
            int quietHoursStart,
            int quietHoursEnd,
            int staleReminderHours,
            int deadlineReminderMinutesBefore
    ) {}
}
