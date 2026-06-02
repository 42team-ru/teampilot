package ru.team42.backend.room_common.internal;

import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.scheduling.TaskScheduler;
import ru.team42.backend.room_common.context.RoomContext;
import ru.team42.backend.room_common.handler.RoomHandler;
import ru.team42.backend.room_common.model.RoomSession;

import java.util.Collections;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * Один запущенный экземпляр комнаты.
 *
 * Весь код обработчика выполняется в однопоточном исполнителе — блокировки не требуются
 * внутри обработчиков. Параллельные кадры WebSocket ставятся в очередь и обрабатываются последовательно.
 */
@Slf4j
public class RoomInstance<S> {

    private final String roomId;
    private final RoomHandler<S> handler;
    private volatile S state;
    private final Map<String, RoomSession> participants = new ConcurrentHashMap<>();
    private final ExecutorService executor;
    private final SimpMessagingTemplate messagingTemplate;
    private final TaskScheduler taskScheduler;
    private final ObjectMapper objectMapper;
    private volatile boolean closed = false;

    public RoomInstance(String roomId,
                        RoomHandler<S> handler,
                        SimpMessagingTemplate messagingTemplate,
                        TaskScheduler taskScheduler,
                        ObjectMapper objectMapper) {
        this.roomId = roomId;
        this.handler = handler;
        this.state = handler.initialState();
        this.messagingTemplate = messagingTemplate;
        this.taskScheduler = taskScheduler;
        this.objectMapper = objectMapper;
        this.executor = Executors.newSingleThreadExecutor(r -> {
            Thread t = new Thread(r, "room-" + handler.getRoomType() + "-" + roomId);
            t.setDaemon(true);
            return t;
        });
    }

    /** Отправляет задачу последовательному исполнителю комнаты. Ничего не делает, если комната закрыта. */
    public void submit(Runnable task) {
        if (closed) return;
        executor.submit(() -> {
            try {
                task.run();
            } catch (Exception e) {
                log.error("[room={}/{}] unhandled executor error", handler.getRoomType(), roomId, e);
            }
        });
    }

    public void addParticipant(RoomSession session) {
        participants.put(session.getSessionId(), session);
    }

    public void removeParticipant(String sessionId) {
        participants.remove(sessionId);
    }

    public boolean isEmpty() { return participants.isEmpty(); }

    public RoomContext contextFor(RoomSession session) {
        return new RoomContextImpl<>(session, this);
    }

    public void close() {
        closed = true;
        executor.shutdown();
    }

    public boolean isClosed() { return closed; }
    public String getRoomId() { return roomId; }
    public RoomHandler<S> getHandler() { return handler; }
    public S getState() { return state; }
    public Map<String, RoomSession> getParticipants() { return Collections.unmodifiableMap(participants); }
    public SimpMessagingTemplate getMessagingTemplate() { return messagingTemplate; }
    public TaskScheduler getTaskScheduler() { return taskScheduler; }
    public ObjectMapper getObjectMapper() { return objectMapper; }
}
