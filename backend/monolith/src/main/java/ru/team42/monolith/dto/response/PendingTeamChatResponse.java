package ru.team42.monolith.dto.response;

import ru.team42.monolith.entity.PendingTeamChat;
import ru.team42.monolith.entity.enums.PendingTeamChatStatus;

import java.time.Instant;
import java.util.UUID;

public record PendingTeamChatResponse(
        UUID id,
        Long telegramChatId,
        String chatTitle,
        PendingTeamChatStatus status,
        UUID linkedTeamId,
        Instant linkedAt,
        Instant lastSeenAt
) {
    public static PendingTeamChatResponse from(PendingTeamChat chat) {
        return new PendingTeamChatResponse(
                chat.getId(),
                chat.getTelegramChatId(),
                chat.getChatTitle(),
                chat.getStatus(),
                chat.getLinkedTeam() != null ? chat.getLinkedTeam().getId() : null,
                chat.getLinkedAt(),
                chat.getLastSeenAt()
        );
    }
}
