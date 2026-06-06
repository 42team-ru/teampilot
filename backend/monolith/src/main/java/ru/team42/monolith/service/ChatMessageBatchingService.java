package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.monolith.entity.ChatMessage;
import ru.team42.monolith.entity.TaskColumn;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.repository.ChatMessageRepository;
import ru.team42.monolith.repository.TaskColumnRepository;
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
    private final TaskColumnRepository taskColumnRepository;

    @Scheduled(fixedDelay = 5_000)
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

            Team team = teamRepository.findByTelegramChatId(chatId).orElse(null);
            if (team == null) {
                log.warn("No team found for chatId={}, skipping batch", chatId);
                continue;
            }

            List<TeamUser> teamMembers = teamUserRepository.findByTeamId(team.getId());
            List<TaskColumn> columns = taskColumnRepository.findByTeamId(team.getId());

            batchPublisher.publishBatch(team.getId().toString(), messages, teamMembers, columns);
            messages.forEach(m -> m.setSentToLlmAt(now));
            chatMessageRepository.saveAll(messages);

            log.info("Flushed batch: teamId={} chatId={} size={} reason={} teamSize={} columns={}",
                    team.getId(), chatId, messages.size(),
                    sizeThresholdReached ? "size" : "timeout",
                    teamMembers.size(), columns.size());
        }
    }

}
