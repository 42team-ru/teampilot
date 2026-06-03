package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.TeamUser;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface TeamUserRepository extends JpaRepository<TeamUser, UUID> {

    Optional<TeamUser> findByTeamIdAndUserTelegramId(UUID teamId, Long telegramId);

    List<TeamUser> findByTeamId(UUID teamId);
}
