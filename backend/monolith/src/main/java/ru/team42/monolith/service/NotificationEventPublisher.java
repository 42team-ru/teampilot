package ru.team42.monolith.service;

import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.AbstractEventPublisher;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.event.BotNotificationEvent;

@Component
public class NotificationEventPublisher extends AbstractEventPublisher {

    public void publishDeadlineReminder(Task task) {
        Long telegramId = task.getAssignee().getUser().getTelegramId();
        Long chatId = task.getTeam().getTelegramChatId();
        send(
                KafkaTopics.BOTS_NOTIFICATIONS,
                task.getId().toString(),
                new BotNotificationEvent(
                        telegramId,
                        chatId,
                        BotNotificationEvent.TYPE_DEADLINE,
                        task.getId(),
                        task.getTitle()
                )
        );
    }

    public void publishStaleAlert(Task task) {
        Long telegramId = task.getAssignee().getUser().getTelegramId();
        Long chatId = task.getTeam().getTelegramChatId();
        send(
                KafkaTopics.BOTS_NOTIFICATIONS,
                task.getId().toString(),
                new BotNotificationEvent(
                        telegramId,
                        chatId,
                        BotNotificationEvent.TYPE_STALE,
                        task.getId(),
                        task.getTitle()
                )
        );
    }
}
