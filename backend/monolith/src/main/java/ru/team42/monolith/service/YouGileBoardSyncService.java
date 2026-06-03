package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.TaskStatusHistory;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.enums.TaskLocalStatus;
import ru.team42.monolith.entity.enums.TaskSource;
import ru.team42.monolith.entity.enums.TaskStatus;
import ru.team42.monolith.entity.enums.TaskSyncStatus;
import ru.team42.monolith.kanban.YouGileService;
import ru.team42.monolith.repository.TaskRepository;
import ru.team42.monolith.repository.TaskStatusHistoryRepository;
import ru.team42.monolith.repository.TeamUserRepository;

import java.util.List;
import java.util.Optional;

@Slf4j
@Service
@RequiredArgsConstructor
public class YouGileBoardSyncService {

    private final YouGileService youGileService;
    private final TaskRepository taskRepository;
    private final TaskStatusHistoryRepository historyRepository;
    private final TeamUserRepository teamUserRepository;

    @Transactional
    public void syncTeam(Team team) {
        if (team.getKanbanId() == null || team.getKanbanApiKey() == null) return;

        List<YouGileService.YouGileTaskResponse> remoteTasks = youGileService.fetchAllTasksForBoard(team);
        for (YouGileService.YouGileTaskResponse remote : remoteTasks) {
            try {
                syncRemoteTask(team, remote);
            } catch (Exception e) {
                log.warn("Failed to sync YouGile task {} for team {}: {}", remote.getId(), team.getId(), e.getMessage());
            }
        }
        log.info("Board sync done for team {} — {} remote tasks processed", team.getId(), remoteTasks.size());
    }

    private void syncRemoteTask(Team team, YouGileService.YouGileTaskResponse remote) {
        Optional<Task> existing = taskRepository.findByTeamIdAndExternalId(team.getId(), remote.getId());
        if (existing.isPresent()) {
            updateTask(team, existing.get(), remote);
        } else {
            importTask(team, remote);
        }
    }

    private void updateTask(Team team, Task task, YouGileService.YouGileTaskResponse remote) {
        boolean changed = false;

        if (remote.getColumnId() != null) {
            String columnName = youGileService.resolveColumnName(team, remote.getColumnId());
            TaskStatus newStatus = youGileService.resolveInternalStatus(team, remote.getColumnId());

            if (newStatus != task.getStatus()) {
                recordHistory(task, task.getStatus(), newStatus);
                task.setStatus(newStatus);
                changed = true;
            }

            if (columnName != null && !columnName.equals(task.getYougileStatus())) {
                task.setYougileStatus(columnName);
                changed = true;
            }
        }

        if (remote.getTitle() != null && !remote.getTitle().equals(task.getTitle())) {
            task.setTitle(remote.getTitle());
            changed = true;
        }

        if (remote.getResponsible() != null) {
            teamUserRepository.findByTeamIdAndYougileUserId(team.getId(), remote.getResponsible())
                    .ifPresent(tu -> {
                        if (!tu.equals(task.getAssignee())) {
                            task.setAssignee(tu);
                        }
                    });
        }

        if (changed) {
            taskRepository.save(task);
        }
    }

    private void importTask(Team team, YouGileService.YouGileTaskResponse remote) {
        Task task = new Task();
        task.setTeam(team);
        task.setTitle(remote.getTitle() != null ? remote.getTitle() : "Untitled");
        task.setExternalId(remote.getId());
        task.setSyncStatus(TaskSyncStatus.SYNCED);
        task.setSource(TaskSource.YOUGILE);
        task.setLocalStatus(TaskLocalStatus.ACTIVE);

        if (remote.getColumnId() != null) {
            task.setStatus(youGileService.resolveInternalStatus(team, remote.getColumnId()));
            task.setYougileStatus(youGileService.resolveColumnName(team, remote.getColumnId()));
        }

        if (remote.getResponsible() != null) {
            teamUserRepository.findByTeamIdAndYougileUserId(team.getId(), remote.getResponsible())
                    .ifPresent(task::setAssignee);
        }

        task = taskRepository.save(task);
        recordHistory(task, null, task.getStatus());
        log.info("Imported YouGile task {} as local task {} for team {}", remote.getId(), task.getId(), team.getId());
    }

    private void recordHistory(Task task, TaskStatus from, TaskStatus to) {
        TaskStatusHistory h = new TaskStatusHistory();
        h.setTask(task);
        h.setFromStatus(from);
        h.setToStatus(to);
        historyRepository.save(h);
    }
}
