package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.dto.response.UserStatsResponse;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.entity.UserAchievement;
import ru.team42.monolith.entity.UserProfile;
import ru.team42.monolith.entity.enums.AchievementType;
import ru.team42.monolith.repository.TaskRepository;
import ru.team42.monolith.repository.UserAchievementRepository;
import ru.team42.monolith.repository.UserProfileRepository;
import ru.team42.monolith.repository.UserRepository;

import java.time.Duration;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;

@Service
@RequiredArgsConstructor
public class GamificationService {

    private static final int MAX_LEVEL = 6;

    private final UserProfileRepository userProfileRepository;
    private final UserAchievementRepository userAchievementRepository;
    private final TaskRepository taskRepository;
    private final UserRepository userRepository;
    private final NotificationEventPublisher notificationEventPublisher;

    @Transactional
    public void onTaskCompleted(Task task) {
        if (task.getAssignee() == null || task.getAssignee().getUser() == null) {
            return;
        }

        User user = task.getAssignee().getUser();
        UserProfile profile = getOrCreate(user);
        int previousLevel = levelFromXp(profile.getXp());

        updateStreak(profile);
        long taskXp = computeXp(task, profile.getStreak());
        profile.setXp(profile.getXp() + taskXp);

        List<AchievementType> awarded = checkAndAwardAchievements(user, task, profile);
        userProfileRepository.save(profile);

        for (AchievementType achievement : awarded) {
            notificationEventPublisher.publishAchievement(user, achievement, profile.getXp());
        }

        int newLevel = levelFromXp(profile.getXp());
        if (newLevel > previousLevel) {
            notificationEventPublisher.publishLevelUp(user, levelName(newLevel), profile.getXp());
        }
    }

    @Transactional(readOnly = true)
    public UserStatsResponse getUserStats(Long telegramId) {
        User user = userRepository.findByTelegramId(telegramId)
                .orElseThrow(() -> AppException.notFound(
                        "User with Telegram ID %d not found".formatted(telegramId)
                ));

        UserProfile profile = userProfileRepository.findByUserId(user.getId()).orElse(null);
        long completedCount = taskRepository.countByAssigneeUserTelegramIdAndCompletedTrueAndDeletedFalse(telegramId);
        long overdueCompleted = taskRepository.countOverdueCompleted(telegramId);
        long overdueCount = overdueCompleted + taskRepository.countStillOverdue(telegramId, Instant.now());
        double onTimeRate = completedCount == 0
                ? 0.0
                : Math.max(0.0, (completedCount - overdueCompleted) / (double) completedCount);

        long xp = profile != null ? profile.getXp() : 0L;
        int level = levelFromXp(xp);

        List<UserStatsResponse.AchievementDto> achievements = userAchievementRepository
                .findByUserIdOrderByAwardedAtDesc(user.getId())
                .stream()
                .map(this::toAchievementDto)
                .toList();

        return new UserStatsResponse(
                completedCount,
                overdueCount,
                onTimeRate,
                profile != null ? profile.getStreak() : 0,
                xp,
                level,
                levelName(level),
                xpForCurrentLevel(level),
                xpForNextLevel(level),
                achievements
        );
    }

    public static int levelFromXp(long xp) {
        double normalizedXp = Math.max(0L, xp) / 100.0;
        int computed = (int) Math.floor(Math.sqrt(normalizedXp));
        return Math.min(MAX_LEVEL, Math.max(1, computed));
    }

    public static String levelName(int level) {
        return switch (Math.min(MAX_LEVEL, Math.max(1, level))) {
            case 2 -> "Исполнитель";
            case 3 -> "Специалист";
            case 4 -> "Профессионал";
            case 5 -> "Эксперт";
            case 6 -> "Легенда";
            default -> "Новобранец";
        };
    }

    public static long xpForCurrentLevel(int level) {
        int normalized = Math.min(MAX_LEVEL, Math.max(1, level));
        if (normalized == 1) {
            return 0L;
        }
        return (long) normalized * normalized * 100L;
    }

    public static long xpForNextLevel(int level) {
        int normalized = Math.min(MAX_LEVEL, Math.max(1, level));
        return (long) (normalized + 1) * (normalized + 1) * 100L;
    }

    private UserProfile getOrCreate(User user) {
        return userProfileRepository.findByUserId(user.getId())
                .orElseGet(() -> {
                    UserProfile profile = new UserProfile();
                    profile.setUser(user);
                    return profile;
                });
    }

    private void updateStreak(UserProfile profile) {
        LocalDate today = LocalDate.now(ZoneOffset.UTC);
        if (profile.getLastActiveDate() == null) {
            profile.setStreak(1);
        } else if (profile.getLastActiveDate().equals(today.minusDays(1))) {
            profile.setStreak(profile.getStreak() + 1);
        } else if (!profile.getLastActiveDate().equals(today)) {
            profile.setStreak(1);
        }
        profile.setLastActiveDate(today);
    }

    private long computeXp(Task task, int streak) {
        Instant completedAt = completedAt(task);
        boolean onTime = task.getDeadline() != null && !completedAt.isAfter(task.getDeadline());
        boolean early = onTime && Duration.between(completedAt, task.getDeadline()).toHours() >= 24;
        long base = onTime ? 100L : 20L;
        if (early) {
            base += 50L;
        }
        double multiplier = Math.min(1.0 + (streak - 1) * 0.1, 2.0);
        return Math.round(base * multiplier);
    }

    private List<AchievementType> checkAndAwardAchievements(User user, Task task, UserProfile profile) {
        List<AchievementType> awarded = new ArrayList<>();
        for (AchievementType achievement : AchievementType.values()) {
            if (userAchievementRepository.existsByUserIdAndAchievementKey(user.getId(), achievement.name())) {
                continue;
            }
            if (!isUnlocked(achievement, user, task, profile)) {
                continue;
            }

            UserAchievement userAchievement = new UserAchievement();
            userAchievement.setUser(user);
            userAchievement.setAchievementKey(achievement.name());
            userAchievement.setAwardedAt(Instant.now());
            userAchievementRepository.save(userAchievement);

            profile.setXp(profile.getXp() + achievement.getXpReward());
            awarded.add(achievement);
        }
        return awarded;
    }

    private boolean isUnlocked(AchievementType achievement, User user, Task task, UserProfile profile) {
        Long telegramId = user.getTelegramId();
        return switch (achievement) {
            case FIRST_STEP -> telegramId != null
                    && taskRepository.countByAssigneeUserTelegramIdAndCompletedTrueAndDeletedFalse(telegramId) >= 1;
            case LIGHTNING -> completedBeforeHalfTime(task);
            case EARLY_BIRD -> completedAtLeastDayBeforeDeadline(task);
            case WEEK_STREAK -> profile.getStreak() >= 7;
            case SNIPER -> telegramId != null && latestTenCompletedOnTime(telegramId);
            case MOUNTAIN -> telegramId != null
                    && taskRepository.countByAssigneeUserTelegramIdAndCompletedTrueAndDeletedFalse(telegramId) >= 50;
            case CLEAN_MONTH -> telegramId != null && hasCleanMonth(telegramId)
                    && taskRepository.countByAssigneeUserTelegramIdAndCompletedTrueAndDeletedFalse(telegramId) > 0;
        };
    }

    private boolean completedBeforeHalfTime(Task task) {
        if (task.getDeadline() == null || task.getCreatedAt() == null) {
            return false;
        }
        Instant createdAt = task.getCreatedAt().toInstant(ZoneOffset.UTC);
        Instant completedAt = completedAt(task);
        if (!completedAt.isBefore(task.getDeadline())) {
            return false;
        }

        Duration allocated = Duration.between(createdAt, task.getDeadline());
        if (allocated.isZero() || allocated.isNegative()) {
            return false;
        }

        Instant halfTime = createdAt.plus(allocated.dividedBy(2));
        return completedAt.isBefore(halfTime);
    }

    private boolean completedAtLeastDayBeforeDeadline(Task task) {
        if (task.getDeadline() == null) {
            return false;
        }
        Instant completedAt = completedAt(task);
        return !completedAt.isAfter(task.getDeadline())
                && Duration.between(completedAt, task.getDeadline()).toHours() >= 24;
    }

    private boolean latestTenCompletedOnTime(Long telegramId) {
        List<Task> latestCompleted = taskRepository
                .findTop10ByAssigneeUserTelegramIdAndCompletedTrueAndDeletedFalseOrderByUpdatedAtDesc(telegramId);
        return latestCompleted.size() >= 10 && latestCompleted.stream().allMatch(this::isOnTime);
    }

    private boolean hasCleanMonth(Long telegramId) {
        Instant now = Instant.now();
        Instant since = now.minus(Duration.ofDays(30));
        LocalDateTime sinceLocal = LocalDateTime.ofInstant(since, ZoneOffset.UTC);
        long overdue = taskRepository.countOverdueCompletedSince(telegramId, sinceLocal)
                + taskRepository.countStillOverdueSince(telegramId, since, now);
        return overdue == 0;
    }

    private boolean isOnTime(Task task) {
        return task.getDeadline() != null && !completedAt(task).isAfter(task.getDeadline());
    }

    private Instant completedAt(Task task) {
        if (task.getUpdatedAt() == null) {
            return Instant.now();
        }
        return task.getUpdatedAt().toInstant(ZoneOffset.UTC);
    }

    private UserStatsResponse.AchievementDto toAchievementDto(UserAchievement userAchievement) {
        AchievementType achievement = null;
        try {
            achievement = AchievementType.valueOf(userAchievement.getAchievementKey());
        } catch (IllegalArgumentException ignored) {
            // Preserve unknown historical achievements instead of failing /profile.
        }

        return new UserStatsResponse.AchievementDto(
                userAchievement.getAchievementKey(),
                achievement != null ? achievement.getEmoji() : "",
                achievement != null ? achievement.getName() : userAchievement.getAchievementKey(),
                userAchievement.getAwardedAt()
        );
    }
}
