package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.dto.request.AdminCreateTeamRequest;
import ru.team42.monolith.dto.request.CreatePendingTeamChatRequest;
import ru.team42.monolith.dto.request.UpdateTeamRequest;
import ru.team42.monolith.dto.response.PendingTeamChatResponse;
import ru.team42.monolith.dto.response.TeamResponse;
import ru.team42.monolith.entity.PendingTeamChat;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.entity.enums.PendingTeamChatStatus;
import ru.team42.monolith.entity.enums.SystemRole;
import ru.team42.monolith.entity.enums.TeamRole;
import ru.team42.monolith.mapper.TeamMapper;
import ru.team42.monolith.repository.PendingTeamChatRepository;
import ru.team42.monolith.repository.TeamRepository;
import ru.team42.monolith.repository.TeamUserRepository;
import ru.team42.monolith.repository.UserRepository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class TeamService {

    private final TeamRepository teamRepository;
    private final TeamUserRepository teamUserRepository;
    private final UserRepository userRepository;
    private final PendingTeamChatRepository pendingTeamChatRepository;
    private final TeamMapper teamMapper;

    public List<TeamResponse> getManagerTeams(Long telegramId) {
        return teamUserRepository.findAllByUserTelegramIdAndRole(telegramId, TeamRole.MANAGER)
                .stream()
                .map(TeamUser::getTeam)
                .map(teamMapper::toResponse)
                .toList();
    }

    @Transactional
    public TeamResponse update(UUID teamId, UpdateTeamRequest req, Long managerTelegramId) {
        Team team = teamRepository.findById(teamId)
                .orElseThrow(() -> AppException.notFound("Team with teamId %d not found".formatted(teamId)));
        requireManager(teamId, managerTelegramId);

        if (req.telegramChatId() != null) team.setTelegramChatId(req.telegramChatId());
        if (req.chatTitle() != null) team.setChatTitle(req.chatTitle());
        if (req.kanbanId() != null) team.setKanbanId(req.kanbanId());
        if (req.kanbanApiKey() != null) team.setKanbanApiKey(req.kanbanApiKey());

        Team saved = teamRepository.save(team);
        if (req.telegramChatId() != null) {
            markPendingChatLinked(req.telegramChatId(), saved);
        }
        return teamMapper.toResponse(saved);
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
        markPendingChatRemoved(telegramChatId);
    }

    @Transactional
    public PendingTeamChatResponse upsertPendingChat(Long managerTelegramId, CreatePendingTeamChatRequest req) {
        User manager = userRepository.findByTelegramId(managerTelegramId)
                .orElseThrow(() -> AppException.unauthorized("Telegram user %d not found".formatted(managerTelegramId)));
        Instant now = Instant.now();
        PendingTeamChat chat = pendingTeamChatRepository.findByTelegramChatId(req.telegramChatId())
                .orElseGet(PendingTeamChat::new);

        chat.setTelegramChatId(req.telegramChatId());
        chat.setChatTitle(req.chatTitle());
        chat.setAddedBy(manager);
        chat.setStatus(PendingTeamChatStatus.PENDING);
        chat.setLinkedTeam(null);
        chat.setLinkedAt(null);
        chat.setLastSeenAt(now);

        return PendingTeamChatResponse.from(pendingTeamChatRepository.save(chat));
    }

    @Transactional(readOnly = true)
    public List<PendingTeamChatResponse> getMyPendingChats(Long managerTelegramId) {
        return pendingTeamChatRepository
                .findAllByAddedByTelegramIdAndStatus(managerTelegramId, PendingTeamChatStatus.PENDING)
                .stream()
                .map(PendingTeamChatResponse::from)
                .toList();
    }

    @Transactional
    public void markPendingChatLinked(Long telegramChatId, Team team) {
        pendingTeamChatRepository.findByTelegramChatId(telegramChatId).ifPresent(chat -> {
            Instant now = Instant.now();
            chat.setStatus(PendingTeamChatStatus.LINKED);
            chat.setLinkedTeam(team);
            chat.setLinkedAt(now);
            chat.setLastSeenAt(now);
            pendingTeamChatRepository.save(chat);
        });
    }

    @Transactional
    public void markPendingChatRemoved(Long telegramChatId) {
        pendingTeamChatRepository.findByTelegramChatId(telegramChatId).ifPresent(chat -> {
            chat.setStatus(PendingTeamChatStatus.REMOVED);
            chat.setLastSeenAt(Instant.now());
            pendingTeamChatRepository.save(chat);
        });
    }

    private void requireManager(UUID teamId, Long telegramId) {
        if (telegramId == null) {
            throw AppException.unauthorized("Telegram user is required");
        }
        boolean manager = teamUserRepository.findByTeamIdAndUserTelegramId(teamId, telegramId)
                .map(teamUser -> teamUser.getRole() == TeamRole.MANAGER)
                .orElse(false);
        if (!manager) {
            throw AppException.forbidden("Only team manager can update team %s".formatted(teamId));
        }
    }
}
