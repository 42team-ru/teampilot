package ru.team42.backend.room_common.internal;

import org.springframework.messaging.simp.SimpMessageHeaderAccessor;
import org.springframework.messaging.simp.SimpMessageType;
import ru.team42.backend.room_common.context.RoomContext;
import ru.team42.backend.room_common.model.OutboundEnvelope;
import ru.team42.backend.room_common.model.RoomSession;

import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.concurrent.ScheduledFuture;

class RoomContextImpl<S> implements RoomContext {

    private final RoomSession session;
    private final RoomInstance<S> instance;

    RoomContextImpl(RoomSession session, RoomInstance<S> instance) {
        this.session = session;
        this.instance = instance;
    }

    @Override
    public RoomSession session() { return session; }

    @Override
    @SuppressWarnings("unchecked")
    public <T> T state() { return (T) instance.getState(); }

    @Override
    public Map<String, RoomSession> participants() { return instance.getParticipants(); }

    @Override
    public void broadcast(String event, Object payload) {
        String destination = "/topic/" + session.getRoomType() + "/" + instance.getRoomId();
        instance.getMessagingTemplate().convertAndSend(destination, new OutboundEnvelope(event, payload));
    }

    @Override
    public void sendTo(String targetSessionId, String event, Object payload) {
        SimpMessageHeaderAccessor accessor = SimpMessageHeaderAccessor.create(SimpMessageType.MESSAGE);
        accessor.setSessionId(targetSessionId);
        accessor.setLeaveMutable(true);
        instance.getMessagingTemplate().convertAndSendToUser(
                targetSessionId,
                "/queue/events",
                new OutboundEnvelope(event, payload),
                accessor.getMessageHeaders()
        );
    }

    @Override
    public ScheduledFuture<?> schedule(Duration delay, Runnable task) {
        return instance.getTaskScheduler().schedule(
                () -> instance.submit(task),
                Instant.now().plus(delay)
        );
    }

    @Override
    public ScheduledFuture<?> scheduleAtFixedRate(Duration period, Runnable task) {
        return instance.getTaskScheduler().scheduleAtFixedRate(
                () -> instance.submit(task),
                period
        );
    }

    @Override
    public void closeRoom() {
        instance.close();
    }
}
