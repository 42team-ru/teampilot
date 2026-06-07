package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.AbstractEventPublisher;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.TaskColumn;
import ru.team42.monolith.event.TaskConfirmationEvent;
import ru.team42.monolith.event.TaskLifecycleEvent;
import ru.team42.monolith.event.TaskStateEvent;

import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class TaskEventPublisher extends AbstractEventPublisher {

    private final TaskNotificationRecipientResolver recipientResolver;

    public void publishConfirmation(Task task, boolean autoConfirmed) {
        String assigneeUsername = assigneeOf(task);
        String columnTitle = task.getColumn() != null ? task.getColumn().getTitle() : null;
        List<Long> recipients = recipientResolver.resolveRecipients(task);
        if (recipients.isEmpty()) {
            log.warn("Skipping task confirmation notification for task {}: no DM recipients", task.getId());
            return;
        }
        send(KafkaTopics.BOTS_TASKS,
                task.getTeam().getId().toString(),
                new TaskConfirmationEvent(
                        task.getId(),
                        recipients,
                        task.getTitle(),
                        task.getDescription(),
                        assigneeUsername,
                        task.getDeadline(),
                        autoConfirmed,
                        columnTitle
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
        String columnTitle = task.getColumn() != null ? task.getColumn().getTitle() : null;
        sendState(task, TaskStateEvent.Type.UPDATED, columnTitle);
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
        List<Long> recipients = recipientResolver.resolveRecipients(task);
        if (recipients.isEmpty()) {
            log.warn("Skipping task state notification for task {}: no DM recipients", task.getId());
            return;
        }
        send(KafkaTopics.TASKS_STATE, task.getTeam().getId().toString(),
                new TaskStateEvent(task.getId(), recipients, type, task.getTitle(),
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
