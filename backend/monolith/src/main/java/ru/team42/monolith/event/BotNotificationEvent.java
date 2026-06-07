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

    private final List<Long> recipientTelegramIds;
    private final String type;
    private final UUID taskId;
    private final String taskTitle;
    private final String achievementName;
    private final String achievementEmoji;
    private final Integer xpGained;
    private final Long newTotalXp;
    private final String newLevelName;

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
            String newLevelName
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
                newLevelName
        );
    }
}
