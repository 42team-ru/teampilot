package ru.team42.monolith.service;

import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class ExcuseService {

    // Map<telegramId, Map<teamId, reason>>
    private final Map<Long, Map<UUID, String>> excuses = new ConcurrentHashMap<>();

    public void excuse(Long telegramId, UUID teamId, String reason) {
        excuses.computeIfAbsent(telegramId, k -> new ConcurrentHashMap<>())
                .put(teamId, reason);
    }

    public void excuseAllTeams(Long telegramId, List<UUID> teamIds, String reason) {
        Map<UUID, String> teamMap = excuses.computeIfAbsent(telegramId, k -> new ConcurrentHashMap<>());
        for (UUID teamId : teamIds) {
            teamMap.put(teamId, reason);
        }
    }

    public boolean isExcused(Long telegramId, UUID teamId) {
        Map<UUID, String> teamMap = excuses.get(telegramId);
        return teamMap != null && teamMap.containsKey(teamId);
    }

    /**
     * Returns Map<telegramId, reason> for all users excused from the given team.
     */
    public Map<Long, String> getExcusedForTeam(UUID teamId) {
        Map<Long, String> result = new HashMap<>();
        for (Map.Entry<Long, Map<UUID, String>> entry : excuses.entrySet()) {
            String reason = entry.getValue().get(teamId);
            if (reason != null) {
                result.put(entry.getKey(), reason);
            }
        }
        return result;
    }

    public void clearTeam(UUID teamId) {
        for (Map<UUID, String> teamMap : excuses.values()) {
            teamMap.remove(teamId);
        }
    }
}
