package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.dto.request.AdminCreateTeamRequest;
import ru.team42.monolith.dto.request.UpdateTeamRequest;
import ru.team42.monolith.dto.response.TeamResponse;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.entity.enums.SystemRole;
import ru.team42.monolith.entity.enums.TeamRole;
import ru.team42.monolith.mapper.TeamMapper;
import ru.team42.monolith.repository.TeamRepository;
import ru.team42.monolith.repository.TeamUserRepository;
import ru.team42.monolith.repository.UserRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class TeamService {

    private final TeamRepository teamRepository;
    private final TeamUserRepository teamUserRepository;
    private final UserRepository userRepository;
    private final TeamMapper teamMapper;

    public List<TeamResponse> getManagerTeams(Long telegramId) {
        return teamUserRepository.findAllByUserTelegramIdAndRole(telegramId, TeamRole.MANAGER)
                .stream()
                .map(TeamUser::getTeam)
                .map(teamMapper::toResponse)
                .toList();
    }

    @Transactional
    public TeamResponse update(UUID teamId, UpdateTeamRequest req) {
        Team team = teamRepository.findById(teamId)
                .orElseThrow(() -> AppException.notFound("Team with teamId %d not found".formatted(teamId)));
        if (req.telegramChatId() != null) team.setTelegramChatId(req.telegramChatId());
        if (req.chatTitle() != null) team.setChatTitle(req.chatTitle());
        if (req.kanbanId() != null) team.setKanbanId(req.kanbanId());
        if (req.kanbanApiKey() != null) team.setKanbanApiKey(req.kanbanApiKey());
        return teamMapper.toResponse(teamRepository.save(team));
    }

    @Transactional
    public TeamResponse createWithAdmin(AdminCreateTeamRequest req) {
        Team team = req.telegramChatId() != null
                ? teamRepository.findByTelegramChatId(req.telegramChatId()).orElseGet(Team::new)
                : new Team();
        team.setTelegramChatId(req.telegramChatId());
        team.setChatTitle(req.chatTitle());
        if (req.kanbanId() != null) team.setKanbanId(req.kanbanId());
        if (req.kanbanApiKey() != null) team.setKanbanApiKey(req.kanbanApiKey());
        team.setActive(true);
        team = teamRepository.save(team);

        User admin = userRepository.findByTelegramId(req.adminTelegramId())
                .orElseGet(() -> {
                    User u = new User();
                    u.setTelegramId(req.adminTelegramId());
                    u.setTelegramLogin(req.adminUsername());
                    u.setSystemRole(SystemRole.SYSTEM_ADMIN);
                    return userRepository.save(u);
                });

        if (teamUserRepository.findByTeamIdAndUserId(team.getId(), admin.getId()).isEmpty()) {
            TeamUser member = new TeamUser();
            member.setTeam(team);
            member.setUser(admin);
            member.setRole(TeamRole.MANAGER);
            teamUserRepository.save(member);
        }

        return teamMapper.toResponse(team);
    }

    public Optional<TeamResponse> findByTelegramChatId(Long telegramChatId) {
        return teamRepository.findByTelegramChatId(telegramChatId).map(teamMapper::toResponse);
    }

    @Transactional
    public void deactivate(Long telegramChatId) {
        teamRepository.findByTelegramChatId(telegramChatId).ifPresent(team -> {
            team.setActive(false);
            teamRepository.save(team);
        });
    }
}
