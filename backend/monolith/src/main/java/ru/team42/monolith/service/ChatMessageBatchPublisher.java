package ru.team42.monolith.service;

import com.google.protobuf.Timestamp;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.backend.proto.events.MessageBatchProto;
import ru.team42.monolith.entity.ChatMessage;
import ru.team42.monolith.entity.TaskColumn;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.entity.YouGileSticker;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

@Component
public class ChatMessageBatchPublisher {

    private final KafkaTemplate<String, byte[]> protoKafkaTemplate;

    public ChatMessageBatchPublisher(
            @Qualifier("protoKafkaTemplate") KafkaTemplate<String, byte[]> protoKafkaTemplate) {
        this.protoKafkaTemplate = protoKafkaTemplate;
    }

    public void publishBatch(String teamId, List<ChatMessage> messages,
                             List<TeamUser> teamMembers,
                             List<TaskColumn> columns,
                             List<YouGileSticker> stickers) {
        var event = MessageBatchProto.MessageBatchEvent.newBuilder()
                .setEventId(UUID.randomUUID().toString())
                .setOccurredAt(toTimestamp(Instant.now()))
                .setTeamId(teamId)
                .setBatchStart(toTimestamp(messages.getFirst().getMessageTimestamp()))
                .setBatchEnd(toTimestamp(messages.getLast().getMessageTimestamp()))
                .addAllMessages(messages.stream().map(this::toProtoMessage).toList())
                .addAllTeam(teamMembers.stream().map(this::toProtoMember).toList())
                .addAllColumns(columns.stream().map(this::toProtoColumn).toList())
                .addAllStickers(stickers.stream().map(this::toProtoSticker).toList())
                .build();

        protoKafkaTemplate.send(KafkaTopics.MESSAGES_BATCHES, teamId, event.toByteArray());
    }

    private MessageBatchProto.MessageBatchEvent.MessageDto toProtoMessage(ChatMessage m) {
        var user = m.getTeamUser().getUser();
        return MessageBatchProto.MessageBatchEvent.MessageDto.newBuilder()
                .setUserId(user.getTelegramId())
                .setUsername(nullToEmpty(user.getTelegramLogin()))
                .setFullName(buildFullName(user.getFirstName(), user.getLastName()))
                .setText(m.getText())
                .setTimestamp(toTimestamp(m.getMessageTimestamp()))
                .setMessageId(m.getId().toString())
                .build();
    }

    private MessageBatchProto.MessageBatchEvent.TeamMemberDto toProtoMember(TeamUser tu) {
        return MessageBatchProto.MessageBatchEvent.TeamMemberDto.newBuilder()
                .setTelegramId(tu.getUser().getTelegramId())
                .setUsername(nullToEmpty(tu.getUser().getTelegramLogin()))
                .setFullName(buildFullName(tu.getUser().getFirstName(), tu.getUser().getLastName()))
                .setRole(tu.getRole().name())
                .setPosition(nullToEmpty(tu.getPosition()))
                .build();
    }

    private MessageBatchProto.MessageBatchEvent.ColumnDto toProtoColumn(TaskColumn col) {
        return MessageBatchProto.MessageBatchEvent.ColumnDto.newBuilder()
                .setId(col.getId().toString())
                .setTitle(col.getTitle())
                .build();
    }

    private static Timestamp toTimestamp(Instant instant) {
        return Timestamp.newBuilder()
                .setSeconds(instant.getEpochSecond())
                .setNanos(instant.getNano())
                .build();
    }

    private static String buildFullName(String first, String last) {
        String f = first != null ? first : "";
        String l = last != null ? " " + last : "";
        return (f + l).trim();
    }

    private MessageBatchProto.MessageBatchEvent.StickerDef toProtoSticker(YouGileSticker s) {
        var builder = MessageBatchProto.MessageBatchEvent.StickerDef.newBuilder()
                .setId(s.getYougileStickerId())
                .setTitle(s.getTitle())
                .setType(s.getType().name());
        if (s.getStates() != null) {
            s.getStates().forEach(state -> builder.addStates(
                    MessageBatchProto.MessageBatchEvent.StickerStateDef.newBuilder()
                            .setId(state.getYougileStateId())
                            .setTitle(state.getTitle())
                            .build()
            ));
        }
        return builder.build();
    }

    private static String nullToEmpty(String s) {
        return s != null ? s : "";
    }
}
