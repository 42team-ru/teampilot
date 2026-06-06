package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.AbstractEventPublisher;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.entity.enums.AchievementType;
import ru.team42.monolith.event.BotNotificationEvent;

import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class NotificationEventPublisher extends AbstractEventPublisher {

    private final TaskNotificationRecipientResolver recipientResolver;

    public void publishDeadlineReminder(Task task) {
        List<Long> recipients = recipientResolver.resolveRecipients(task);
        if (recipients.isEmpty()) {
            log.warn("Skipping deadline reminder for task {}: no DM recipients", task.getId());
            return;
        }
        send(
                KafkaTopics.BOTS_NOTIFICATIONS,
                task.getId().toString(),
                new BotNotificationEvent(
                        recipients,
                        BotNotificationEvent.TYPE_DEADLINE,
                        task.getId(),
                        task.getTitle()
                )
        );
    }

    public void publishStaleAlert(Task task) {
        List<Long> recipients = recipientResolver.resolveRecipients(task);
        if (recipients.isEmpty()) {
            log.warn("Skipping stale alert for task {}: no DM recipients", task.getId());
            return;
        }
        send(
                KafkaTopics.BOTS_NOTIFICATIONS,
                task.getId().toString(),
                new BotNotificationEvent(
                        recipients,
                        BotNotificationEvent.TYPE_STALE,
                        task.getId(),
                        task.getTitle()
                )
        );
    }

    public void publishAchievement(User user, AchievementType achievement, long newTotalXp) {
        if (user.getTelegramId() == null) {
            log.warn("Skipping achievement notification for user {}: no Telegram ID", user.getId());
            return;
        }
        send(
                KafkaTopics.BOTS_NOTIFICATIONS,
                user.getTelegramId().toString(),
                BotNotificationEvent.achievement(
                        List.of(user.getTelegramId()),
                        achievement,
                        newTotalXp
                )
        );
    }

    public void publishLevelUp(User user, String newLevelName, long newTotalXp) {
        if (user.getTelegramId() == null) {
            log.warn("Skipping level-up notification for user {}: no Telegram ID", user.getId());
            return;
        }
        send(
                KafkaTopics.BOTS_NOTIFICATIONS,
                user.getTelegramId().toString(),
                BotNotificationEvent.levelUp(
                        List.of(user.getTelegramId()),
                        newLevelName,
                        newTotalXp
                )
        );
    }
}
