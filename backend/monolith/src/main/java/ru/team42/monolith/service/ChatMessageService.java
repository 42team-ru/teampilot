package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.monolith.event.ChatMessageEvent;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.mapper.ChatMessageMapper;
import ru.team42.monolith.repository.ChatMessageRepository;
import ru.team42.monolith.repository.TeamRepository;
import ru.team42.monolith.repository.UserRepository;

import java.util.List;
import java.util.Optional;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChatMessageService {

    private final ChatMessageRepository chatMessageRepository;
    private final ChatMessageMapper chatMessageMapper;
    private final UserRepository userRepository;
    private final TeamRepository teamRepository;

    @Transactional
    public void saveAll(List<ChatMessageEvent> events) {
        events.forEach(this::save);
    }

    @Transactional
    public void save(ChatMessageEvent event) {
        Optional<Team> teamOpt = teamRepository.findByTelegramChatId(event.getChatId());
        if (teamOpt.isEmpty()) {
            log.warn("No team found for chatId={}, dropping message", event.getChatId());
            return;
        }
        User user = findOrCreateUser(event);
        chatMessageRepository.save(chatMessageMapper.toEntity(event, user, teamOpt.get()));
    }

    private User findOrCreateUser(ChatMessageEvent event) {
        return userRepository.findByTelegramId(event.getUserId())
                .orElseGet(() -> {
                    var user = new User();
                    user.setTelegramId(event.getUserId());
                    user.setTelegramLogin(event.getUsername());
                    String[] parts = event.getFullName() != null
                            ? event.getFullName().split(" ", 2)
                            : new String[]{"", null};
                    user.setFirstName(parts[0]);
                    user.setLastName(parts.length > 1 ? parts[1] : null);
                    return userRepository.save(user);
                });
    }
}
