package ru.team42.backend.room_common.example.notification;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import ru.team42.backend.room_common.example.notification.dto.ClearAllDto;
import ru.team42.backend.room_common.example.notification.dto.MarkReadDto;
import ru.team42.backend.room_common.support.TestRoom;

import java.time.Instant;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("NotificationRoom")
class NotificationRoomTest {

    private NotificationRoom room;

    @BeforeEach
    void setUp() {
        room = new NotificationRoom();
    }

    @Test
    @DisplayName("onConnect — отправляет только непрочитанные уведомления")
    void onConnect_sendsOnlyUnread() {
        var state = room.initialState();
        state.add(new Notification("1", "Деплой завершён", "Сервис запущен", Instant.now()));
        state.add(new Notification("2", "Ошибка", "DB недоступна", Instant.now()));
        state.markRead("1"); // первое уже прочитано

        var testRoom = new TestRoom<>(state);
        var ctx = testRoom.ctx("alice");
        room.onConnect(ctx);

        assertThat(testRoom.hasSentTo("alice", "INITIAL_STATE")).isTrue();

        var msg = testRoom.sentTo("alice").getFirst();
        @SuppressWarnings("unchecked")
        var payload = (java.util.Map<String, Object>) msg.payload();
        assertThat(payload.get("unreadCount")).isEqualTo(1);
    }

    @Test
    @DisplayName("onConnect — без уведомлений: unreadCount = 0")
    void onConnect_emptyState_sendsZeroCount() {
        var testRoom = new TestRoom<>(room.initialState());
        var ctx = testRoom.ctx("bob");
        room.onConnect(ctx);

        assertThat(testRoom.hasSentTo("bob", "INITIAL_STATE")).isTrue();
        @SuppressWarnings("unchecked")
        var payload = (java.util.Map<String, Object>) testRoom.sentTo("bob").getFirst().payload();
        assertThat(payload.get("unreadCount")).isEqualTo(0);
    }

    @Test
    @DisplayName("MARK_READ — уведомление помечается прочитанным, broadcast NOTIFICATION_READ")
    void markRead_marksNotificationAndBroadcasts() {
        var state = room.initialState();
        state.add(new Notification("42", "Встреча", "Завтра в 10:00", Instant.now()));

        var testRoom = new TestRoom<>(state);
        var ctx = testRoom.ctx("alice");

        var dto = new MarkReadDto();
        dto.setNotificationId("42");
        testRoom.dispatch(room, ctx, "MARK_READ", dto);

        assertThat(testRoom.getState().getUnread()).isEmpty();
        assertThat(testRoom.hasBroadcast("NOTIFICATION_READ")).isTrue();

        var broadcast = testRoom.lastBroadcast("NOTIFICATION_READ");
        assertThat(broadcast.payload().toString()).contains("42");
    }

    @Test
    @DisplayName("MARK_READ — повторный вызов для уже прочитанного не даёт broadcast")
    void markRead_alreadyRead_noBroadcast() {
        var state = room.initialState();
        state.add(new Notification("7", "Тест", "Тело", Instant.now()));
        state.markRead("7");

        var testRoom = new TestRoom<>(state);
        var ctx = testRoom.ctx("alice");

        var dto = new MarkReadDto();
        dto.setNotificationId("7");
        testRoom.dispatch(room, ctx, "MARK_READ", dto);

        assertThat(testRoom.hasBroadcast("NOTIFICATION_READ")).isFalse();
    }

    @Test
    @DisplayName("CLEAR_ALL — все уведомления удаляются, broadcast ALL_CLEARED")
    void clearAll_removesAllAndBroadcasts() {
        var state = room.initialState();
        state.add(new Notification("1", "A", "body", Instant.now()));
        state.add(new Notification("2", "B", "body", Instant.now()));

        var testRoom = new TestRoom<>(state);
        var ctx = testRoom.ctx("alice");
        testRoom.dispatch(room, ctx, "CLEAR_ALL", new ClearAllDto());

        assertThat(testRoom.getState().getAll()).isEmpty();
        assertThat(testRoom.hasBroadcast("ALL_CLEARED")).isTrue();
    }

    @Test
    @DisplayName("push — добавляет уведомление в состояние и рассылает broadcast")
    void push_addsAndBroadcasts() {
        var testRoom = new TestRoom<>(room.initialState());
        var ctx = testRoom.ctx("alice");

        room.push(ctx, "Новое событие", "Что-то произошло");

        assertThat(testRoom.getState().getAll()).hasSize(1);
        assertThat(testRoom.getState().getAll().getFirst().isRead()).isFalse();
        assertThat(testRoom.hasBroadcast("NOTIFICATION")).isTrue();
    }

    @Test
    @DisplayName("push × N — история накапливается, непрочитанных столько же")
    void push_multiple_accumulates() {
        var testRoom = new TestRoom<>(room.initialState());
        var ctx = testRoom.ctx("alice");

        room.push(ctx, "Уведомление 1", "...");
        room.push(ctx, "Уведомление 2", "...");
        room.push(ctx, "Уведомление 3", "...");

        assertThat(testRoom.getState().getAll()).hasSize(3);
        assertThat(testRoom.getState().getUnread()).hasSize(3);
        assertThat(testRoom.broadcastsOf("NOTIFICATION")).hasSize(3);
    }
}
