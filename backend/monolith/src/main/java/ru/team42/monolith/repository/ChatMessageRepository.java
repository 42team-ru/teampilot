package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import ru.team42.monolith.entity.ChatMessage;

import java.util.List;
import java.util.UUID;

public interface ChatMessageRepository extends JpaRepository<ChatMessage, UUID> {

    @Query("SELECT DISTINCT m.chatId FROM ChatMessage m WHERE m.sentToLlmAt IS NULL")
    List<Long> findDistinctChatIdsWithUnprocessedMessages();

    @Query("SELECT m FROM ChatMessage m WHERE m.chatId = :chatId AND m.sentToLlmAt IS NULL ORDER BY m.messageTimestamp ASC")
    List<ChatMessage> findUnprocessedByChatId(Long chatId);
}
