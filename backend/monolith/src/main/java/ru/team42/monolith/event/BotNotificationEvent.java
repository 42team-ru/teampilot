package ru.team42.monolith.event;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Getter;
import ru.team42.backend.kafka_common.event.BaseEvent;
import ru.team42.monolith.entity.enums.AchievementType;

import java.util.List;
import java.util.UUID;

@Getter
@JsonInclude(JsonInclude.Include.NON_NULL)
public class BotNotificationEvent extends BaseEvent {

    public static final String TYPE_DEADLINE = "DEADLINE";
    public static final String TYPE_STALE = "STALE";
    public static final String TYPE_ACHIEVEMENT = "ACHIEVEMENT";
    public static final String TYPE_LEVEL_UP = "LEVEL_UP";
    public static final String TYPE_COURSE_RECOMMENDATION = "COURSE_RECOMMENDATION";
    public static final String TYPE_MEETING_SUMMARY = "MEETING_SUMMARY";

    public record CourseInfo(String courseId, String title, String url, String description) {}

    private final List<Long> recipientTelegramIds;
    private final String type;
    private final UUID taskId;
    private final String taskTitle;
    private final String achievementName;
    private final String achievementEmoji;
    private final Integer xpGained;
    private final Long newTotalXp;
    private final String newLevelName;
    private final List<CourseInfo> courses;
    private final String meetingId;
    private final String meetingTitle;
    private final String meetingSummary;
    private final List<String> meetingTasks;
    private final List<String> meetingHints;

    public BotNotificationEvent(List<Long> recipientTelegramIds, String type, UUID taskId, String taskTitle) {
        this(
                recipientTelegramIds,
                type,
                taskId,
                taskTitle,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null
        );
    }

    private BotNotificationEvent(
            List<Long> recipientTelegramIds,
            String type,
            UUID taskId,
            String taskTitle,
            String achievementName,
            String achievementEmoji,
            Integer xpGained,
            Long newTotalXp,
            String newLevelName,
            List<CourseInfo> courses,
            String meetingId,
            String meetingTitle,
            String meetingSummary,
            List<String> meetingTasks,
            List<String> meetingHints
    ) {
        this.recipientTelegramIds = recipientTelegramIds;
        this.type = type;
        this.taskId = taskId;
        this.taskTitle = taskTitle;
        this.achievementName = achievementName;
        this.achievementEmoji = achievementEmoji;
        this.xpGained = xpGained;
        this.newTotalXp = newTotalXp;
        this.newLevelName = newLevelName;
        this.courses = courses;
        this.meetingId = meetingId;
        this.meetingTitle = meetingTitle;
        this.meetingSummary = meetingSummary;
        this.meetingTasks = meetingTasks;
        this.meetingHints = meetingHints;
    }

    public static BotNotificationEvent achievement(
            List<Long> recipientTelegramIds,
            AchievementType achievement,
            long newTotalXp
    ) {
        return new BotNotificationEvent(
                recipientTelegramIds,
                TYPE_ACHIEVEMENT,
                null,
                null,
                achievement.getName(),
                achievement.getEmoji(),
                achievement.getXpReward(),
                newTotalXp,
                null,
                null,
                null,
                null,
                null,
                null,
                null
        );
    }

    public static BotNotificationEvent levelUp(
            List<Long> recipientTelegramIds,
            String newLevelName,
            long newTotalXp
    ) {
        return new BotNotificationEvent(
                recipientTelegramIds,
                TYPE_LEVEL_UP,
                null,
                null,
                null,
                null,
                null,
                newTotalXp,
                newLevelName,
                null,
                null,
                null,
                null,
                null,
                null
        );
    }

    public static BotNotificationEvent courseRecommendation(
            List<Long> recipientTelegramIds,
            String taskTitle,
            List<CourseInfo> courses
    ) {
        return new BotNotificationEvent(
                recipientTelegramIds,
                TYPE_COURSE_RECOMMENDATION,
                null,
                taskTitle,
                null,
                null,
                null,
                null,
                null,
                courses,
                null,
                null,
                null,
                null,
                null
        );
    }

    public static BotNotificationEvent meetingSummary(
            Long telegramChatId,
            String meetingId,
            String meetingTitle,
            String meetingSummary,
            List<String> meetingTasks,
            List<String> meetingHints
    ) {
        return new BotNotificationEvent(
                List.of(telegramChatId),
                TYPE_MEETING_SUMMARY,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                null,
                meetingId,
                meetingTitle,
                meetingSummary,
                meetingTasks,
                meetingHints
        );
    }
}
