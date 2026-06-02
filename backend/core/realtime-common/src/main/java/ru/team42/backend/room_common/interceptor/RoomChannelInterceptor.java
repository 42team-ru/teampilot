package ru.team42.backend.room_common.interceptor;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.Message;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.simp.stomp.StompCommand;
import org.springframework.messaging.simp.stomp.StompHeaderAccessor;
import org.springframework.messaging.support.ChannelInterceptor;
import ru.team42.backend.room_common.config.RoomProperties;
import ru.team42.backend.room_common.event.EventDescriptor;
import ru.team42.backend.room_common.internal.RoomInstance;
import ru.team42.backend.room_common.internal.RoomRegistry;
import ru.team42.backend.room_common.model.RoomEnvelope;
import ru.team42.backend.room_common.model.RoomSession;

import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Направляет STOMP-кадры обработчикам комнат.
 * ПОДПИСАТЬСЯ /topic/{roomType}/{roomId} → onConnect
 * ОТПРАВИТЬ /app/{roomType}/{roomId} → отправка события
 * ОТКЛЮЧИТЬСЯ → onDisconnect + очистка
 */
@Slf4j
public class RoomChannelInterceptor implements ChannelInterceptor {

    private final RoomRegistry registry;
    private final ObjectMapper objectMapper;
    private final String appPrefix;
    private final String topicPrefix;

    /** sessionId → set of "roomType/roomId" keys */
    private final Map<String, Set<String>> sessionRooms = new ConcurrentHashMap<>();

    public RoomChannelInterceptor(RoomRegistry registry,
                                   ObjectMapper objectMapper,
                                   RoomProperties properties) {
        this.registry = registry;
        this.objectMapper = objectMapper;
        this.appPrefix = properties.getAppPrefix();
        this.topicPrefix = properties.getTopicPrefix();
    }

    @Override
    public Message<?> preSend(Message<?> message, MessageChannel channel) {
        StompHeaderAccessor accessor = StompHeaderAccessor.wrap(message);
        StompCommand command = accessor.getCommand();
        if (command == null) return message;

        switch (command) {
            case SUBSCRIBE -> handleSubscribe(accessor);
            case SEND -> handleSend(accessor, message);
            case DISCONNECT, UNSUBSCRIBE -> handleDisconnect(accessor);
            default -> { /* ignore */ }
        }
        return message;
    }

    private void handleSubscribe(StompHeaderAccessor accessor) {
        String destination = accessor.getDestination();
        if (destination == null) return;

        String prefix = topicPrefix + "/";
        if (!destination.startsWith(prefix)) return;

        String[] parts = destination.substring(prefix.length()).split("/", 2);
        if (parts.length != 2) return;

        String roomType = parts[0];
        String roomId   = parts[1];

        if (!registry.isKnownType(roomType)) return;

        String sessionId = accessor.getSessionId();
        Map<String, Object> attrs = accessor.getSessionAttributes();

        String participantId = attrs != null
                ? (String) attrs.getOrDefault(RoomHandshakeInterceptor.PARTICIPANT_ID, UUID.randomUUID().toString())
                : UUID.randomUUID().toString();
        Long userId = attrs != null ? (Long) attrs.get(RoomHandshakeInterceptor.USER_ID) : null;

        RoomSession session = RoomSession.builder()
                .sessionId(sessionId)
                .participantId(participantId)
                .userId(userId)
                .roomType(roomType)
                .roomId(roomId)
                .build();

        RoomInstance<?> instance = registry.getOrCreate(roomType, roomId);
        instance.addParticipant(session);
        sessionRooms.computeIfAbsent(sessionId, k -> ConcurrentHashMap.newKeySet())
                    .add(roomType + "/" + roomId);

        instance.submit(() -> {
            try {
                instance.getHandler().onConnect(instance.contextFor(session));
            } catch (Exception e) {
                instance.getHandler().onError(instance.contextFor(session), e);
            }
        });
    }

    private void handleSend(StompHeaderAccessor accessor, Message<?> message) {
        String destination = accessor.getDestination();
        if (destination == null) return;

        String prefix = appPrefix + "/";
        if (!destination.startsWith(prefix)) return;

        String[] parts = destination.substring(prefix.length()).split("/", 2);
        if (parts.length != 2) return;

        String roomType = parts[0];
        String roomId   = parts[1];

        if (!registry.isKnownType(roomType)) return;

        String sessionId = accessor.getSessionId();
        Optional<RoomInstance<?>> instanceOpt = registry.findInstance(roomType, roomId);
        if (instanceOpt.isEmpty()) return;

        RoomInstance<?> instance = instanceOpt.get();
        RoomSession session = instance.getParticipants().get(sessionId);
        if (session == null) return;

        Object rawPayload = message.getPayload();
        byte[] bytes = rawPayload instanceof byte[] b ? b : rawPayload.toString().getBytes();

        RoomEnvelope envelope;
        try {
            envelope = objectMapper.readValue(bytes, RoomEnvelope.class);
        } catch (Exception e) {
            log.warn("[room-common] failed to parse envelope from session={}", sessionId, e);
            instance.submit(() -> instance.getHandler().onError(instance.contextFor(session), e));
            return;
        }

        instance.submit(() -> dispatch(instance, session, envelope));
    }

    private void handleDisconnect(StompHeaderAccessor accessor) {
        String sessionId = accessor.getSessionId();
        Set<String> rooms = sessionRooms.remove(sessionId);
        if (rooms == null) return;

        for (String roomKey : rooms) {
            String[] parts = roomKey.split("/", 2);
            if (parts.length != 2) continue;

            registry.findInstance(parts[0], parts[1]).ifPresent(instance -> {
                RoomSession session = instance.getParticipants().get(sessionId);
                if (session == null) return;

                instance.submit(() -> {
                    try {
                        instance.getHandler().onDisconnect(instance.contextFor(session));
                    } catch (Exception e) {
                        log.warn("[room-common] onDisconnect error session={}", sessionId, e);
                    }
                    instance.removeParticipant(sessionId);
                    if (instance.isEmpty()) {
                        registry.remove(parts[0], parts[1]);
                    }
                });
            });
        }
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private void dispatch(RoomInstance<?> instance, RoomSession session, RoomEnvelope envelope) {
        String eventName = envelope.getEvent();
        if (eventName == null) return;

        EventDescriptor found = null;
        for (EventDescriptor<?> desc : instance.getHandler().getDescriptors()) {
            if (desc.getName().equals(eventName)) {
                found = desc;
                break;
            }
        }

        if (found == null) {
            log.warn("[room-common] unknown event={} in roomType={}", eventName, instance.getHandler().getRoomType());
            instance.getHandler().onError(
                    instance.contextFor(session),
                    new IllegalArgumentException("Unknown event: " + eventName)
            );
            return;
        }

        Object dto;
        try {
            dto = envelope.getPayload() != null
                    ? instance.getObjectMapper().treeToValue(envelope.getPayload(), found.getPayloadType())
                    : found.getPayloadType().getDeclaredConstructor().newInstance();
        } catch (Exception e) {
            instance.getHandler().onError(instance.contextFor(session), e);
            return;
        }

        try {
            found.getHandler().accept(instance.contextFor(session), dto);
        } catch (Exception e) {
            instance.getHandler().onError(instance.contextFor(session), e);
        }
    }
}
