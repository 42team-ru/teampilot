package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.dto.request.TeamRequest;
import ru.team42.monolith.dto.response.TeamResponse;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.repository.TeamRepository;

import java.util.Optional;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class TeamService {

    private final TeamRepository teamRepository;

    @Transactional
    public TeamResponse create(TeamRequest req) {
        if (teamRepository.findByTelegramChatId(req.telegramChatId()).isPresent()) {
            throw AppException.alreadyExists("Team for chatId %d already exists".formatted(req.telegramChatId()));
        }
        Team team = new Team();
        team.setTelegramChatId(req.telegramChatId());
        team.setChatTitle(req.chatTitle());
        team.setKanbanId(req.kanbanId());
        team.setKanbanApiKey(req.kanbanApiKey());
        return toResponse(teamRepository.save(team));
    }

    public Optional<TeamResponse> findByTelegramChatId(Long telegramChatId) {
        return teamRepository.findByTelegramChatId(telegramChatId).map(this::toResponse);
    }

    public Optional<TeamResponse> findById(UUID id) {
        return teamRepository.findById(id).map(this::toResponse);
    }

    @Transactional
    public void deactivate(Long telegramChatId) {
        teamRepository.findByTelegramChatId(telegramChatId).ifPresent(team -> {
            team.setActive(false);
            teamRepository.save(team);
        });
    }

    private TeamResponse toResponse(Team team) {
        return new TeamResponse(
                team.getId(),
                team.getTelegramChatId(),
                team.getChatTitle(),
                team.getKanbanId(),
                team.isActive()
        );
    }
}
