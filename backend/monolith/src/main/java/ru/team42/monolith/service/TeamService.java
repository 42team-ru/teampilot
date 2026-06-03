package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.monolith.dto.request.TeamRequest;
import ru.team42.monolith.dto.response.TeamResponse;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.repository.TeamRepository;

import java.util.Optional;

@Service
@RequiredArgsConstructor
public class TeamService {

    private final TeamRepository teamRepository;

    @Transactional
    public TeamResponse register(TeamRequest req) {
        Team team = teamRepository.findByTelegramChatId(req.telegramChatId())
                .orElseGet(Team::new);
        team.setTelegramChatId(req.telegramChatId());
        team.setChatTitle(req.chatTitle());
        team.setKanbanId(req.kanbanId());
        team.setKanbanApiKey(req.kanbanApiKey());
        team.setActive(true);
        return toResponse(teamRepository.save(team));
    }

    public Optional<TeamResponse> findByTelegramChatId(Long telegramChatId) {
        return teamRepository.findByTelegramChatId(telegramChatId).map(this::toResponse);
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
