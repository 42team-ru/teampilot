package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.kafka_common.event.ChatMessageEvent;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.mapper.ChatMessageMapper;
import ru.team42.monolith.repository.ChatMessageRepository;
import ru.team42.monolith.repository.UserRepository;

import java.util.List;

@Service
@RequiredArgsConstructor
public class ChatMessageService {

    private final ChatMessageRepository chatMessageRepository;
    private final ChatMessageMapper chatMessageMapper;
    private final UserRepository userRepository;

    @Transactional
    public void saveAll(List<ChatMessageEvent> events) {
        var entities = events.stream()
                .map(event -> chatMessageMapper.toEntity(event, findOrCreateUser(event)))
                .toList();
        chatMessageRepository.saveAll(entities);
    }

    @Transactional
    public void save(ChatMessageEvent event) {
        chatMessageRepository.save(chatMessageMapper.toEntity(event, findOrCreateUser(event)));
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
