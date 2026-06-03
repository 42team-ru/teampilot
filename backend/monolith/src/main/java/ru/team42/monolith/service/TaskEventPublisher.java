package ru.team42.monolith.service;

import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.AbstractEventPublisher;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.event.TaskConfirmationEvent;

@Component
public class TaskEventPublisher extends AbstractEventPublisher {

    public void publishConfirmation(Task task) {
        String assigneeUsername = task.getAssignee() != null
                ? task.getAssignee().getUser().getTelegramLogin()
                : null;

        send(KafkaTopics.BOTS_TASKS,
                task.getTeam().getTelegramChatId().toString(),
                new TaskConfirmationEvent(
                        task.getId(),
                        task.getTeam().getTelegramChatId(),
                        task.getTitle(),
                        task.getDescription(),
                        assigneeUsername,
                        task.getDeadline()
                ));
    }
}
