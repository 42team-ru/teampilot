package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.SyncUserState;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface SyncUserStateRepository extends JpaRepository<SyncUserState, UUID> {

    List<SyncUserState> findBySessionTeamId(UUID teamId);

    Optional<SyncUserState> findByRequestId(String requestId);

    Optional<SyncUserState> findBySessionTeamIdAndTelegramId(UUID teamId, Long telegramId);

    void deleteBySessionTeamId(UUID teamId);

    Optional<SyncUserState> findFirstByTelegramId(Long telegramId);
}
