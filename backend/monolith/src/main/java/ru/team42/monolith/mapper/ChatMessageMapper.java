package ru.team42.monolith.mapper;

import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import ru.team42.monolith.event.ChatMessageEvent;
import ru.team42.monolith.event.MessageBatchEvent;
import ru.team42.monolith.entity.ChatMessage;
import ru.team42.monolith.entity.TeamUser;

@Mapper(componentModel = "spring")
public interface ChatMessageMapper {

    @Mapping(source = "event.timestamp", target = "messageTimestamp")
    @Mapping(source = "event.text", target = "text")
    @Mapping(source = "teamUser", target = "teamUser")
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "sentToLlmAt", ignore = true)
    @Mapping(target = "createdAt", ignore = true)
    @Mapping(target = "updatedAt", ignore = true)
    ChatMessage toEntity(ChatMessageEvent event, TeamUser teamUser);

    @Mapping(source = "teamUser.user.telegramLogin", target = "username")
    @Mapping(source = "messageTimestamp", target = "timestamp")
    @Mapping(target = "fullName", expression =
            "java(chatMessage.getTeamUser().getUser().getFirstName()"
            + " + (chatMessage.getTeamUser().getUser().getLastName() != null"
            + " ? \" \" + chatMessage.getTeamUser().getUser().getLastName() : \"\"))")
    @Mapping(source = "teamUser.user.telegramId", target = "userId")
    MessageBatchEvent.MessageDto toMessageDto(ChatMessage chatMessage);
}
