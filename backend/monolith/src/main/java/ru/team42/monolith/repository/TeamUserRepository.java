package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.entity.enums.TeamRole;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface TeamUserRepository extends JpaRepository<TeamUser, UUID> {
    Optional<TeamUser> findByTeamIdAndUserId(UUID teamId, UUID userId);

    Optional<TeamUser> findByTeamTelegramChatIdAndUserTelegramId(Long telegramChatId, Long telegramId);
    Optional<TeamUser> findByTeamIdAndUserTelegramId(UUID teamId, Long telegramId);

    List<TeamUser> findAllByUserTelegramId(Long telegramId);
    List<TeamUser> findAllByUserTelegramIdAndRole(Long telegramId, TeamRole role);
    Optional<TeamUser> findByTeamIdAndYougileUserId(UUID teamId, String yougileUserId);

    List<TeamUser> findByTeamId(UUID teamId);

    @Query("""
            SELECT tu FROM TeamUser tu
            JOIN FETCH tu.user
            WHERE tu.team.id = :teamId
            """)
    List<TeamUser> findByTeamIdWithUser(@Param("teamId") UUID teamId);
}
