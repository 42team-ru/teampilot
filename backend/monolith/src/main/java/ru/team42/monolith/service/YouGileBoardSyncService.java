package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.TaskColumn;
import ru.team42.monolith.entity.TaskStatusHistory;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.enums.TaskLocalStatus;
import ru.team42.monolith.entity.enums.TaskSource;
import ru.team42.monolith.entity.enums.TaskSyncStatus;
import ru.team42.monolith.kanban.YouGileService;
import ru.team42.monolith.repository.TaskColumnRepository;
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
    private final TaskColumnRepository taskColumnRepository;
    private final TaskStatusHistoryRepository historyRepository;
    private final TeamUserRepository teamUserRepository;

    @Transactional
    public void syncTeam(Team team) {
        if (team.getKanbanId() == null || team.getKanbanApiKey() == null) return;

        syncColumns(team);

        List<YouGileService.YouGileTaskResponse> remoteTasks = youGileService.fetchAllTasksForBoard(team);
        for (YouGileService.YouGileTaskResponse remote : remoteTasks) {
            try {
                syncRemoteTask(team, remote);
            } catch (Exception e) {
                log.warn("Failed to sync YouGile task {} for team {}: {}", remote.id(), team.getId(), e.getMessage());
            }
        }
        log.info("Board sync done for team {} — {} remote tasks processed", team.getId(), remoteTasks.size());
    }

    @Transactional
    public List<TaskColumn> syncColumns(Team team) {
        if (team.getKanbanId() == null || team.getKanbanApiKey() == null) return List.of();

        List<YouGileService.ColumnInfo> remote = youGileService.fetchColumns(team);
        List<TaskColumn> result = new java.util.ArrayList<>();

        for (YouGileService.ColumnInfo info : remote) {
            TaskColumn col = taskColumnRepository
                    .findByTeamIdAndYouGileColumnId(team.getId(), info.id())
                    .orElseGet(TaskColumn::new);

            col.setTeam(team);
            col.setTitle(info.title());
            col.setYouGileColumnId(info.id());

            result.add(taskColumnRepository.save(col));
        }

        log.info("Synced {} columns for team {}", result.size(), team.getId());
        return result;
    }

    private void syncRemoteTask(Team team, YouGileService.YouGileTaskResponse remote) {
        Optional<Task> existing = taskRepository.findByTeamIdAndExternalId(team.getId(), remote.id());
        if (existing.isPresent()) {
            updateTask(team, existing.get(), remote);
        } else {
            importTask(team, remote);
        }
    }

    private void updateTask(Team team, Task task, YouGileService.YouGileTaskResponse remote) {
        boolean changed = false;

        if (remote.columnId() != null) {
            Optional<TaskColumn> colOpt = taskColumnRepository
                    .findByTeamIdAndYouGileColumnId(team.getId(), remote.columnId());
            if (colOpt.isPresent() && !colOpt.get().equals(task.getColumn())) {
                TaskColumn prev = task.getColumn();
                task.setColumn(colOpt.get());
                recordHistory(task, prev, colOpt.get());
                changed = true;
            }
        }

        if (remote.title() != null && !remote.title().equals(task.getTitle())) {
            task.setTitle(remote.title());
            changed = true;
        }

        if (remote.description() != null && !remote.description().equals(task.getDescription())) {
            task.setDescription(remote.description());
            changed = true;
        }

        if (remote.deadline() != null && !remote.deadline().equals(task.getDeadline())) {
            task.setDeadline(remote.deadline());
            changed = true;
        }

        if (remote.responsible() != null) {
            Optional<ru.team42.monolith.entity.TeamUser> assigneeOpt =
                    teamUserRepository.findByTeamIdAndYougileUserId(team.getId(), remote.responsible());
            if (assigneeOpt.isPresent() && !assigneeOpt.get().equals(task.getAssignee())) {
                task.setAssignee(assigneeOpt.get());
                changed = true;
            }
        }

        if (remote.createdBy() != null && task.getAuthor() == null) {
            teamUserRepository.findByTeamIdAndYougileUserId(team.getId(), remote.createdBy())
                    .ifPresent(task::setAuthor);
            changed = true;
        }

        if (changed) {
            taskRepository.save(task);
        }
    }

    private void importTask(Team team, YouGileService.YouGileTaskResponse remote) {
        Task task = new Task();
        task.setTeam(team);
        task.setTitle(remote.title() != null ? remote.title() : "Untitled");
        task.setDescription(remote.description());
        task.setDeadline(remote.deadline());
        task.setExternalId(remote.id());
        task.setSyncStatus(TaskSyncStatus.SYNCED);
        task.setSource(TaskSource.YOUGILE);
        task.setLocalStatus(TaskLocalStatus.ACTIVE);

        TaskColumn column = null;
        if (remote.columnId() != null) {
            column = taskColumnRepository
                    .findByTeamIdAndYouGileColumnId(team.getId(), remote.columnId())
                    .orElse(null);
            task.setColumn(column);
        }

        if (remote.responsible() != null) {
            teamUserRepository.findByTeamIdAndYougileUserId(team.getId(), remote.responsible())
                    .ifPresent(task::setAssignee);
        }

        if (remote.createdBy() != null) {
            teamUserRepository.findByTeamIdAndYougileUserId(team.getId(), remote.createdBy())
                    .ifPresent(task::setAuthor);
        }

        Task saved = taskRepository.save(task);
        recordHistory(saved, null, column);
        log.info("Imported YouGile task {} as local task {} for team {}", remote.id(), saved.getId(), team.getId());
    }

    private void recordHistory(Task task, TaskColumn from, TaskColumn to) {
        TaskStatusHistory h = new TaskStatusHistory();
        h.setTask(task);
        h.setFromColumn(from);
        h.setToColumn(to);
        historyRepository.save(h);
    }
}
