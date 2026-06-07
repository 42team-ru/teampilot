package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.enums.TeamRole;
import ru.team42.monolith.repository.TeamRepository;
import ru.team42.monolith.repository.TeamUserRepository;

@Service
@RequiredArgsConstructor
public class NotificationSettingsService {

    private final TeamRepository teamRepository;
    private final TeamUserRepository teamUserRepository;

    @Transactional(readOnly = true)
    public Team getSettings(Long chatId, Long telegramUserId) {
        return requireManagerTeamByChat(chatId, telegramUserId);
    }

    @Transactional
    public Team updateSettings(Long chatId, Long telegramUserId, ReminderSettingsUpdate update) {
        Team team = requireManagerTeamByChat(chatId, telegramUserId);
        if (update.maxRemindersPerTaskPerDay() != null) {
            team.setReminderMaxPerTaskPerDay(requireRange(update.maxRemindersPerTaskPerDay(), 1, 5, "maxRemindersPerTaskPerDay"));
        }
        if (update.quietHoursStart() != null) {
            team.setReminderQuietHoursStart(requireRange(update.quietHoursStart(), 0, 23, "quietHoursStart"));
        }
        if (update.quietHoursEnd() != null) {
            team.setReminderQuietHoursEnd(requireRange(update.quietHoursEnd(), 0, 23, "quietHoursEnd"));
        }
        if (update.staleReminderHours() != null) {
            team.setStaleReminderHours(requireRange(update.staleReminderHours(), 1, 168, "staleReminderHours"));
        }
        if (update.deadlineReminderMinutesBefore() != null) {
            team.setDeadlineReminderMinutesBefore(requireRange(update.deadlineReminderMinutesBefore(), 5, 1440, "deadlineReminderMinutesBefore"));
        }
        return teamRepository.save(team);
    }

    private Team requireManagerTeamByChat(Long chatId, Long telegramUserId) {
        if (chatId == null) {
            throw AppException.badRequest("chatId is required");
        }
        if (telegramUserId == null) {
            throw AppException.badRequest("telegramUserId is required");
        }
        Team team = teamRepository.findByTelegramChatIdAndActiveTrue(chatId)
                .orElseThrow(() -> AppException.notFound("Active team not found for chat"));
        teamUserRepository.findByTeamIdAndUserTelegramId(team.getId(), telegramUserId)
                .filter(m -> m.getRole() == TeamRole.MANAGER)
                .orElseThrow(() -> AppException.forbidden("Only team managers can change reminder settings"));
        return team;
    }

    private int requireRange(int value, int min, int max, String field) {
        if (value < min || value > max) {
            throw AppException.badRequest("%s must be between %d and %d".formatted(field, min, max));
        }
        return value;
    }

    public record ReminderSettingsUpdate(
            Integer maxRemindersPerTaskPerDay,
            Integer quietHoursStart,
            Integer quietHoursEnd,
            Integer staleReminderHours,
            Integer deadlineReminderMinutesBefore
    ) {}
}
