package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.PendingTeamChat;
import ru.team42.monolith.entity.enums.PendingTeamChatStatus;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface PendingTeamChatRepository extends JpaRepository<PendingTeamChat, UUID> {
    Optional<PendingTeamChat> findByTelegramChatId(Long telegramChatId);

    List<PendingTeamChat> findAllByAddedByTelegramIdAndStatus(Long telegramId, PendingTeamChatStatus status);
}
