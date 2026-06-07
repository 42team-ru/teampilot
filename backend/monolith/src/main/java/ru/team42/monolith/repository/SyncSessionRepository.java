package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.SyncSession;

import java.util.Optional;
import java.util.UUID;

public interface SyncSessionRepository extends JpaRepository<SyncSession, UUID> {

    Optional<SyncSession> findByChatId(Long chatId);

    boolean existsByChatId(Long chatId);
}
