package ru.team42.monolith.scheduler;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.repository.TeamRepository;
import ru.team42.monolith.service.YouGileBoardSyncService;

import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class YouGileSyncScheduler {

    private final TeamRepository teamRepository;
    private final YouGileBoardSyncService boardSyncService;

    @Scheduled(fixedDelay = 60_000)
    public void syncAllTeams() {
        List<Team> teams = teamRepository.findByActiveTrue();
        log.info("YouGile board sync started for {} active teams", teams.size());
        for (Team team : teams) {
            try {
                boardSyncService.syncTeam(team);
            } catch (Exception e) {
                log.error("YouGile sync failed for team {}: {}", team.getId(), e.getMessage());
            }
        }
    }
}
