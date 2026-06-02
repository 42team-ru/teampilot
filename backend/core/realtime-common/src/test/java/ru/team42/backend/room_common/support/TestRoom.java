package ru.team42.backend.room_common.support;

import ru.team42.backend.room_common.context.RoomContext;
import ru.team42.backend.room_common.event.EventDescriptor;
import ru.team42.backend.room_common.handler.RoomHandler;
import ru.team42.backend.room_common.model.RoomSession;

import java.time.Duration;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Delayed;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * Test helper that simulates a room without Spring WebSocket infrastructure.
 *
 * <p>Usage:
 * <pre>{@code
 * var room = new TestRoom<>(handler.initialState());
 * var ctx  = room.ctx("alice");          // create participant
 * room.dispatch(handler, ctx, "JOIN", dto);
 * room.runScheduledTask(0);              // run first queued task immediately
 * assertThat(room.hasBroadcast("PLAYER_JOINED")).isTrue();
 * }</pre>
 */
public class TestRoom<S> {

    public record BroadcastRecord(String event, Object payload) {}
    public record SendRecord(String targetSessionId, String event, Object payload) {}

    private final S state;
    private final Map<String, RoomSession> participants = new LinkedHashMap<>();
    private final List<BroadcastRecord> broadcasts = new ArrayList<>();
    private final List<SendRecord> personalMessages = new ArrayList<>();
    private final List<Runnable> scheduledTasks = new ArrayList<>();
    private boolean closed = false;

    public TestRoom(S state) {
        this.state = state;
    }

    // -------------------------------------------------------------------------
    // Participant management

    /**
     * Creates (or re-uses) a participant context.
     * sessionId and participantId are both set to the given id for simplicity.
     */
    public RoomContext ctx(String participantId) {
        RoomSession session = RoomSession.builder()
                .sessionId(participantId)
                .participantId(participantId)
                .roomType("test")
                .roomId("test-room")
                .build();
        participants.put(participantId, session);
        return new TestRoomContext(session);
    }

    // -------------------------------------------------------------------------
    // Event dispatch

    /** Invokes the matching event handler directly (bypasses WebSocket infrastructure). */
    @SuppressWarnings({"unchecked", "rawtypes"})
    public void dispatch(RoomHandler<?> handler, RoomContext ctx, String event, Object payload) {
        handler.getDescriptors().stream()
                .filter(d -> d.getName().equals(event))
                .findFirst()
                .map(d -> (EventDescriptor<Object>) d)
                .ifPresentOrElse(
                        d -> d.getHandler().accept(ctx, payload),
                        () -> { throw new IllegalArgumentException("No handler for event: " + event); }
                );
    }

    // -------------------------------------------------------------------------
    // Scheduled tasks

    /** Runs a queued scheduled task by insertion index (0-based). */
    public void runScheduledTask(int index) {
        scheduledTasks.get(index).run();
    }

    /** Runs all currently queued tasks in insertion order. */
    public void runAllScheduledTasks() {
        new ArrayList<>(scheduledTasks).forEach(Runnable::run);
    }

    public int scheduledTaskCount() { return scheduledTasks.size(); }

    // -------------------------------------------------------------------------
    // Assertion helpers — broadcasts

    public boolean hasBroadcast(String event) {
        return broadcasts.stream().anyMatch(r -> r.event().equals(event));
    }

    public List<BroadcastRecord> broadcastsOf(String event) {
        return broadcasts.stream().filter(r -> r.event().equals(event)).toList();
    }

    public BroadcastRecord lastBroadcast(String event) {
        return broadcasts.stream()
                .filter(r -> r.event().equals(event))
                .reduce((a, b) -> b)
                .orElseThrow(() -> new AssertionError("No broadcast with event: " + event));
    }

    public List<BroadcastRecord> allBroadcasts() {
        return Collections.unmodifiableList(broadcasts);
    }

    public void clearBroadcasts() { broadcasts.clear(); }

    // -------------------------------------------------------------------------
    // Assertion helpers — personal messages

    public boolean hasSentTo(String sessionId, String event) {
        return personalMessages.stream()
                .anyMatch(r -> r.targetSessionId().equals(sessionId) && r.event().equals(event));
    }

    public List<SendRecord> sentTo(String sessionId) {
        return personalMessages.stream()
                .filter(r -> r.targetSessionId().equals(sessionId))
                .toList();
    }

    // -------------------------------------------------------------------------
    // State / misc

    public S getState() { return state; }
    public boolean isClosed() { return closed; }
    public Map<String, RoomSession> getParticipants() { return Collections.unmodifiableMap(participants); }

    // -------------------------------------------------------------------------

    private class TestRoomContext implements RoomContext {

        private final RoomSession session;

        TestRoomContext(RoomSession session) { this.session = session; }

        @Override public RoomSession session() { return session; }

        @Override @SuppressWarnings("unchecked") public <T> T state() { return (T) state; }

        @Override public Map<String, RoomSession> participants() {
            return Collections.unmodifiableMap(participants);
        }

        @Override public void broadcast(String event, Object payload) {
            broadcasts.add(new BroadcastRecord(event, payload));
        }

        @Override public void sendTo(String targetSessionId, String event, Object payload) {
            personalMessages.add(new SendRecord(targetSessionId, event, payload));
        }

        @Override public ScheduledFuture<?> schedule(Duration delay, Runnable task) {
            scheduledTasks.add(task);
            return fakeFuture();
        }

        @Override public ScheduledFuture<?> scheduleAtFixedRate(Duration period, Runnable task) {
            scheduledTasks.add(task);
            return fakeFuture();
        }

        @Override public void closeRoom() { closed = true; }
    }

    private static ScheduledFuture<Object> fakeFuture() {
        return new ScheduledFuture<>() {
            @Override public long getDelay(TimeUnit unit) { return 0; }
            @Override public int compareTo(Delayed o) { return 0; }
            @Override public boolean cancel(boolean mayInterrupt) { return true; }
            @Override public boolean isCancelled() { return false; }
            @Override public boolean isDone() { return true; }
            @Override public Object get() throws InterruptedException, ExecutionException { return null; }
            @Override public Object get(long t, TimeUnit u)
                    throws InterruptedException, ExecutionException, TimeoutException { return null; }
        };
    }
}
