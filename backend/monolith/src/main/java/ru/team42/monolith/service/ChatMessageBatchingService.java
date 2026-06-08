package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.monolith.entity.ChatMessage;
import ru.team42.monolith.entity.TaskColumn;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.entity.YouGileSticker;
import ru.team42.monolith.repository.ChatMessageRepository;
import ru.team42.monolith.repository.TaskColumnRepository;
import ru.team42.monolith.repository.TeamUserRepository;
import ru.team42.monolith.repository.YouGileStickerRepository;

import java.time.Duration;
import java.time.Instant;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChatMessageBatchingService {

    @Value("${app.batching.min-messages}")
    private int minMessages;

    @Value("${app.batching.max-age-minutes}")
    private int maxAgeMinutes;

    private final ChatMessageRepository chatMessageRepository;
    private final ChatMessageBatchPublisher batchPublisher;
    private final TeamUserRepository teamUserRepository;
    private final TaskColumnRepository taskColumnRepository;
    private final YouGileStickerRepository stickerRepository;

    @Scheduled(fixedDelay = 5_000)
    @Transactional
    public void flushBatches() {
        List<Team> teams = chatMessageRepository.findDistinctTeamsWithUnprocessedMessages();
        if (teams.isEmpty()) return;

        Instant now = Instant.now();

        for (Team team : teams) {
            List<ChatMessage> messages = chatMessageRepository.findUnprocessedByTeam(team);
            if (messages.isEmpty()) continue;

            Instant oldestMessageTime = messages.getFirst().getMessageTimestamp();
            boolean sizeThresholdReached = messages.size() >= minMessages;
            boolean timeThresholdReached = Duration.between(oldestMessageTime, now).compareTo(Duration.ofMinutes(maxAgeMinutes)) >= 0;

            if (!sizeThresholdReached && !timeThresholdReached) continue;

            List<TeamUser> teamMembers = teamUserRepository.findByTeamId(team.getId());
            List<TaskColumn> columns = taskColumnRepository.findByTeamId(team.getId());
            List<YouGileSticker> stickers = stickerRepository.findByTeamIdWithStates(team.getId());

            batchPublisher.publishBatch(team.getId().toString(), messages, teamMembers, columns, stickers);
            messages.forEach(m -> m.setSentToLlmAt(now));
            chatMessageRepository.saveAll(messages);

            log.info("Flushed batch: teamId={} size={} reason={} teamSize={} columns={} stickers={}",
                    team.getId(), messages.size(),
                    sizeThresholdReached ? "size" : "timeout",
                    teamMembers.size(), columns.size(), stickers.size());
        }
    }
}
