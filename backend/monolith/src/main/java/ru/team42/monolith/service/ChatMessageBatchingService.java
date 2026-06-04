package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.monolith.entity.ChatMessage;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.kanban.YouGileService;
import ru.team42.monolith.repository.ChatMessageRepository;
import ru.team42.monolith.repository.TeamRepository;
import ru.team42.monolith.repository.TeamUserRepository;

import java.time.Duration;
import java.time.Instant;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChatMessageBatchingService {

    private static final int MIN_MESSAGES = 10;
    private static final Duration MAX_AGE = Duration.ofMinutes(5);

    private final ChatMessageRepository chatMessageRepository;
    private final ChatMessageBatchPublisher batchPublisher;
    private final TeamRepository teamRepository;
    private final TeamUserRepository teamUserRepository;
    private final YouGileService youGileService;

    @Scheduled(fixedDelay = 60_000)
    @Transactional
    public void flushBatches() {
        List<Long> chatIds = chatMessageRepository.findDistinctChatIdsWithUnprocessedMessages();
        if (chatIds.isEmpty()) return;

        Instant now = Instant.now();

        for (Long chatId : chatIds) {
            List<ChatMessage> messages = chatMessageRepository.findUnprocessedByChatId(chatId);
            if (messages.isEmpty()) continue;

            Instant oldestMessageTime = messages.getFirst().getMessageTimestamp();
            boolean sizeThresholdReached = messages.size() >= MIN_MESSAGES;
            boolean timeThresholdReached = Duration.between(oldestMessageTime, now).compareTo(MAX_AGE) >= 0;

            if (!sizeThresholdReached && !timeThresholdReached) continue;

            List<TeamUser> teamMembers = loadTeamMembers(chatId);
            List<YouGileService.ColumnInfo> columns = loadColumns(chatId);

            batchPublisher.publishBatch(chatId, messages, teamMembers, columns);
            messages.forEach(m -> m.setSentToLlmAt(now));
            chatMessageRepository.saveAll(messages);

            log.info("Flushed batch: chatId={} size={} reason={} teamSize={} columns={}",
                    chatId, messages.size(),
                    sizeThresholdReached ? "size" : "timeout",
                    teamMembers.size(), columns.size());
        }
    }

    private List<TeamUser> loadTeamMembers(Long chatId) {
        return teamRepository.findByTelegramChatId(chatId)
                .map(team -> teamUserRepository.findByTeamId(team.getId()))
                .orElse(List.of());
    }

    private List<YouGileService.ColumnInfo> loadColumns(Long chatId) {
        return teamRepository.findByTelegramChatId(chatId)
                .map(youGileService::fetchColumns)
                .orElse(List.of());
    }
}
