package ru.team42.monolith.service;

import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.AbstractEventPublisher;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.backend.kafka_common.event.MessageBatchEvent;
import ru.team42.monolith.entity.ChatMessage;
import ru.team42.monolith.mapper.ChatMessageMapper;

import java.util.List;

@Component
public class ChatMessageBatchPublisher extends AbstractEventPublisher {

    private final ChatMessageMapper chatMessageMapper;

    public ChatMessageBatchPublisher(ChatMessageMapper chatMessageMapper) {
        this.chatMessageMapper = chatMessageMapper;
    }

    public void publishBatch(Long chatId, List<ChatMessage> messages) {
        var event = MessageBatchEvent.builder()
                .chatId(chatId)
                .messages(messages.stream().map(chatMessageMapper::toMessageDto).toList())
                .batchStart(messages.getFirst().getMessageTimestamp())
                .batchEnd(messages.getLast().getMessageTimestamp())
                .build();
        send(KafkaTopics.MESSAGES_BATCHES, String.valueOf(chatId), event);
    }
}
