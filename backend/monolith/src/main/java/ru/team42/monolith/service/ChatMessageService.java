package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.kafka_common.event.ChatMessageEvent;
import ru.team42.monolith.mapper.ChatMessageMapper;
import ru.team42.monolith.repository.ChatMessageRepository;

import java.util.List;

@Service
@RequiredArgsConstructor
public class ChatMessageService {

    private final ChatMessageRepository chatMessageRepository;
    private final ChatMessageMapper chatMessageMapper;

    @Transactional
    public void saveAll(List<ChatMessageEvent> events) {
        chatMessageRepository.saveAll(chatMessageMapper.toEntities(events));
    }
}
