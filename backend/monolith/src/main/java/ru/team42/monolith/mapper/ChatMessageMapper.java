package ru.team42.monolith.mapper;

import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import ru.team42.backend.kafka_common.event.ChatMessageEvent;
import ru.team42.monolith.entity.ChatMessage;

import java.util.List;

@Mapper(componentModel = "spring")
public interface ChatMessageMapper {

    @Mapping(source = "timestamp", target = "messageTimestamp")
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "userId", ignore = true)
    @Mapping(target = "createdAt", ignore = true)
    @Mapping(target = "updatedAt", ignore = true)
    ChatMessage toEntity(ChatMessageEvent event);

    List<ChatMessage> toEntities(List<ChatMessageEvent> events);
}
