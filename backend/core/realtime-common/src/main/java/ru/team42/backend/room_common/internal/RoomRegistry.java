package ru.team42.backend.room_common.internal;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.scheduling.TaskScheduler;
import ru.team42.backend.room_common.handler.RoomHandler;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
public class RoomRegistry {

    private final Map<String, RoomHandler<?>> handlersByType = new HashMap<>();
    private final Map<String, RoomInstance<?>> instances = new ConcurrentHashMap<>();

    private final SimpMessagingTemplate messagingTemplate;
    private final TaskScheduler taskScheduler;
    private final ObjectMapper objectMapper;

    public RoomRegistry(SimpMessagingTemplate messagingTemplate,
                        TaskScheduler taskScheduler,
                        ObjectMapper objectMapper) {
        this.messagingTemplate = messagingTemplate;
        this.taskScheduler = taskScheduler;
        this.objectMapper = objectMapper;
    }

    public void register(RoomHandler<?> handler) {
        handlersByType.put(handler.getRoomType(), handler);
        log.info("[room-common] registered handler for roomType={}", handler.getRoomType());
    }

    public boolean isKnownType(String roomType) {
        return handlersByType.containsKey(roomType);
    }

    public Optional<RoomInstance<?>> findInstance(String roomType, String roomId) {
        return Optional.ofNullable(instances.get(key(roomType, roomId)));
    }

    @SuppressWarnings({"rawtypes", "unchecked"})
    public RoomInstance<?> getOrCreate(String roomType, String roomId) {
        return instances.computeIfAbsent(key(roomType, roomId), k -> {
            RoomHandler handler = handlersByType.get(roomType);
            if (handler == null) {
                throw new IllegalStateException("No RoomHandler registered for type: " + roomType);
            }
            log.debug("[room-common] creating instance roomType={} roomId={}", roomType, roomId);
            return new RoomInstance<>(roomId, handler, messagingTemplate, taskScheduler, objectMapper);
        });
    }

    public void remove(String roomType, String roomId) {
        RoomInstance<?> instance = instances.remove(key(roomType, roomId));
        if (instance != null) {
            instance.close();
            log.debug("[room-common] removed instance roomType={} roomId={}", roomType, roomId);
        }
    }

    private String key(String type, String id) { return type + "/" + id; }
}
