package ru.team42.monolith.service;

import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.AbstractEventPublisher;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.TaskColumn;
import ru.team42.monolith.event.TaskConfirmationEvent;
import ru.team42.monolith.event.TaskLifecycleEvent;
import ru.team42.monolith.event.TaskStateEvent;

@Component
public class TaskEventPublisher extends AbstractEventPublisher {

    public void publishConfirmation(Task task, boolean autoConfirmed) {
        String assigneeUsername = assigneeOf(task);
        send(KafkaTopics.BOTS_TASKS,
                task.getTeam().getTelegramChatId().toString(),
                new TaskConfirmationEvent(
                        task.getId(),
                        task.getTeam().getTelegramChatId(),
                        task.getTitle(),
                        task.getDescription(),
                        assigneeUsername,
                        task.getDeadline(),
                        autoConfirmed
                ));
    }

    public void publishCreated(Task task) {
        String columnTitle = task.getColumn() != null ? task.getColumn().getTitle() : null;
        sendState(task, TaskStateEvent.Type.CREATED, columnTitle);
        sendLifecycle(task, TaskLifecycleEvent.Type.CONFIRMED);
    }

    public void publishCancelled(Task task) {
        sendState(task, TaskStateEvent.Type.CANCELLED, null);
        sendLifecycle(task, TaskLifecycleEvent.Type.CANCELLED);
    }

    public void publishUpdated(Task task) {
        sendLifecycle(task, TaskLifecycleEvent.Type.UPDATED);
    }

    public void publishImported(Task task) {
        sendLifecycle(task, TaskLifecycleEvent.Type.CONFIRMED);
    }

    public void publishColumnChanged(Task task, TaskColumn newColumn) {
        sendState(task, TaskStateEvent.Type.COLUMN_CHANGED,
                newColumn != null ? newColumn.getTitle() : null);
    }

    private void sendState(Task task, TaskStateEvent.Type type, String columnTitle) {
        Long chatId = task.getTeam().getTelegramChatId();
        if (chatId == null) return;
        send(KafkaTopics.TASKS_STATE, task.getTeam().getId().toString(),
                new TaskStateEvent(task.getId(), chatId, type, task.getTitle(),
                        columnTitle, assigneeOf(task), task.getDeadline()));
    }

    private void sendLifecycle(Task task, TaskLifecycleEvent.Type type) {
        send(KafkaTopics.TASKS_LIFECYCLE, task.getTeam().getId().toString(),
                new TaskLifecycleEvent(task.getId(), task.getTeam().getId(),
                        type, task.getTitle(), task.getDescription()));
    }

    private String assigneeOf(Task task) {
        return task.getAssignee() != null
                ? task.getAssignee().getUser().getTelegramLogin()
                : null;
    }
}
