package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.entity.enums.TeamRole;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface TeamUserRepository extends JpaRepository<TeamUser, UUID> {
    Optional<TeamUser> findByTeamIdAndUserId(UUID teamId, UUID userId);

    Optional<TeamUser> findByTeamTelegramChatIdAndUserTelegramId(Long telegramChatId, Long telegramId);

    List<TeamUser> findAllByUserTelegramIdAndRole(Long telegramId, TeamRole role);
}
