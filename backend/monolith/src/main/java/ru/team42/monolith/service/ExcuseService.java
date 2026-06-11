package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.monolith.entity.SyncExcuse;
import ru.team42.monolith.repository.SyncExcuseRepository;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class ExcuseService {

    private final SyncExcuseRepository syncExcuseRepository;

    @Transactional
    public void excuse(Long telegramId, UUID teamId, String reason) {
        if (!syncExcuseRepository.existsByTelegramIdAndTeamIdAndExcuseDate(telegramId, teamId, LocalDate.now())) {
            SyncExcuse excuse = new SyncExcuse();
            excuse.setTelegramId(telegramId);
            excuse.setTeamId(teamId);
            excuse.setReason(reason);
            excuse.setExcuseDate(LocalDate.now());
            syncExcuseRepository.save(excuse);
        }
    }

    @Transactional
    public void excuseAllTeams(Long telegramId, List<UUID> teamIds, String reason) {
        for (UUID teamId : teamIds) {
            excuse(telegramId, teamId, reason);
        }
    }

    @Transactional(readOnly = true)
    public boolean isExcused(Long telegramId, UUID teamId) {
        return syncExcuseRepository.existsByTelegramIdAndTeamIdAndExcuseDate(telegramId, teamId, LocalDate.now());
    }

    /**
     * Returns Map<telegramId, reason> for all users excused from the given team.
     */
    @Transactional(readOnly = true)
    public Map<Long, String> getExcusedForTeam(UUID teamId) {
        return syncExcuseRepository.findByTeamIdAndExcuseDate(teamId, LocalDate.now())
                .stream()
                .collect(Collectors.toMap(SyncExcuse::getTelegramId, SyncExcuse::getReason));
    }

    @Transactional
    public void clearTeam(UUID teamId) {
        syncExcuseRepository.deleteByTeamIdAndExcuseDate(teamId, LocalDate.now());
    }
}
