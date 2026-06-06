package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.entity.enums.TeamRole;
import ru.team42.monolith.repository.TeamUserRepository;

import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.UUID;

@Component
@RequiredArgsConstructor
public class TaskNotificationRecipientResolver {

    private final TeamUserRepository teamUserRepository;

    public List<Long> resolveRecipients(Task task) {
        UUID teamId = task.getTeam().getId();
        UUID assigneeId = task.getAssignee() != null ? task.getAssignee().getId() : null;
        List<TeamUser> members = teamUserRepository.findByTeamIdWithUser(teamId);
        Set<Long> recipients = new LinkedHashSet<>();

        for (TeamUser member : members) {
            if (member.getRole() == TeamRole.MANAGER) {
                addTelegramId(recipients, member);
            }
        }

        if (assigneeId != null) {
            for (TeamUser member : members) {
                if (assigneeId.equals(member.getId())) {
                    addTelegramId(recipients, member);
                    break;
                }
            }
        } else {
            for (TeamUser member : members) {
                addTelegramId(recipients, member);
            }
        }

        return List.copyOf(recipients);
    }

    private void addTelegramId(Set<Long> recipients, TeamUser member) {
        if (member.getUser() == null || member.getUser().getTelegramId() == null) {
            return;
        }
        recipients.add(member.getUser().getTelegramId());
    }
}
