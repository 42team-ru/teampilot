package ru.team42.monolith.mapper;

import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import ru.team42.backend.kafka_common.event.ChatMessageEvent;
import ru.team42.backend.kafka_common.event.MessageBatchEvent;
import ru.team42.monolith.entity.ChatMessage;
import ru.team42.monolith.entity.User;

@Mapper(componentModel = "spring")
public interface ChatMessageMapper {

    @Mapping(source = "event.timestamp", target = "messageTimestamp")
    @Mapping(source = "event.chatId", target = "chatId")
    @Mapping(source = "event.text", target = "text")
    @Mapping(source = "user", target = "user")
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "sentToLlmAt", ignore = true)
    @Mapping(target = "createdAt", ignore = true)
    @Mapping(target = "updatedAt", ignore = true)
    ChatMessage toEntity(ChatMessageEvent event, User user);

    @Mapping(source = "user.telegramLogin", target = "username")
    @Mapping(source = "messageTimestamp", target = "timestamp")
    @Mapping(target = "fullName", expression =
            "java(chatMessage.getUser().getFirstName()"
            + " + (chatMessage.getUser().getLastName() != null"
            + " ? \" \" + chatMessage.getUser().getLastName() : \"\"))")
    @Mapping(source = "user.telegramId", target = "userId")
    MessageBatchEvent.MessageDto toMessageDto(ChatMessage chatMessage);
}
