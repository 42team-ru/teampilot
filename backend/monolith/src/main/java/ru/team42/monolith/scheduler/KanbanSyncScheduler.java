package ru.team42.monolith.scheduler;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import ru.team42.monolith.entity.KanbanBoard;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.kanban.KanbanAdapterRegistry;
import ru.team42.monolith.repository.TaskRepository;
import ru.team42.monolith.service.TaskService;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Polls external kanban boards every 5 minutes and syncs task statuses into our DB.
 * YouGile (and any other registered provider) is the source of truth for status.
 * The board is already JOIN FETCH-ed in findAllActiveSyncedTasks — no extra DB round-trip needed.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class KanbanSyncScheduler {

    private final TaskRepository taskRepository;
    private final KanbanAdapterRegistry adapterRegistry;
    private final TaskService taskService;

    @Scheduled(fixedRateString = "${app.kanban.sync-rate-ms:300000}")
    public void syncAll() {
        List<Task> activeTasks = taskRepository.findAllActiveSyncedTasks();
        if (activeTasks.isEmpty()) return;

        log.info("KanbanSync: checking {} active task(s) against external boards", activeTasks.size());

        Map<UUID, List<Task>> byBoard = activeTasks.stream()
                .collect(Collectors.groupingBy(t -> t.getBoard().getId()));

        byBoard.forEach((boardId, tasks) -> {
            // Board is already loaded via JOIN FETCH — use it directly from any task in the group
            KanbanBoard board = tasks.getFirst().getBoard();

            if (!adapterRegistry.supports(board.getProvider())) {
                log.debug("No adapter for provider {}, skipping board {}", board.getProvider(), boardId);
                return;
            }

            List<String> externalIds = tasks.stream()
                    .map(Task::getExternalTaskId)
                    .toList();

            Map<String, String> externalStatuses = adapterRegistry.get(board.getProvider())
                    .getExternalStatuses(board, externalIds);

            tasks.forEach(task -> {
                String latestExternalStatus = externalStatuses.get(task.getExternalTaskId());
                if (latestExternalStatus == null) return;

                if (!latestExternalStatus.equals(task.getExternalStatus())) {
                    log.info("KanbanSync: task {} external status '{}' -> '{}'",
                            task.getId(), task.getExternalStatus(), latestExternalStatus);
                    taskService.syncStatusFromExternal(task.getId(), latestExternalStatus);
                }
            });
        });
    }
}
