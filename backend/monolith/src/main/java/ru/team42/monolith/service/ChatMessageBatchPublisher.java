package ru.team42.monolith.service;

import com.google.protobuf.Timestamp;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.backend.proto.events.MessageBatchProto;
import ru.team42.monolith.entity.ChatMessage;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.kanban.YouGileService;

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

    public void publishBatch(Long chatId, List<ChatMessage> messages,
                             List<TeamUser> teamMembers,
                             List<YouGileService.ColumnInfo> columns) {
        var event = MessageBatchProto.MessageBatchEvent.newBuilder()
                .setEventId(UUID.randomUUID().toString())
                .setOccurredAt(toTimestamp(Instant.now()))
                .setChatId(chatId)
                .setBatchStart(toTimestamp(messages.getFirst().getMessageTimestamp()))
                .setBatchEnd(toTimestamp(messages.getLast().getMessageTimestamp()))
                .addAllMessages(messages.stream().map(this::toProtoMessage).toList())
                .addAllTeam(teamMembers.stream().map(this::toProtoMember).toList())
                .addAllColumns(columns.stream().map(this::toProtoColumn).toList())
                .build();

        protoKafkaTemplate.send(KafkaTopics.MESSAGES_BATCHES, String.valueOf(chatId), event.toByteArray());
    }

    private MessageBatchProto.MessageBatchEvent.MessageDto toProtoMessage(ChatMessage m) {
        return MessageBatchProto.MessageBatchEvent.MessageDto.newBuilder()
                .setUserId(m.getUser().getTelegramId())
                .setUsername(nullToEmpty(m.getUser().getTelegramLogin()))
                .setFullName(buildFullName(m.getUser().getFirstName(), m.getUser().getLastName()))
                .setText(m.getText())
                .setTimestamp(toTimestamp(m.getMessageTimestamp()))
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

    private MessageBatchProto.MessageBatchEvent.ColumnDto toProtoColumn(YouGileService.ColumnInfo col) {
        return MessageBatchProto.MessageBatchEvent.ColumnDto.newBuilder()
                .setId(col.id())
                .setTitle(col.title())
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

    private static String nullToEmpty(String s) {
        return s != null ? s : "";
    }
}
