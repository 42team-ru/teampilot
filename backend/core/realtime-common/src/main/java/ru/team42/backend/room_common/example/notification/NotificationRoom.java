package ru.team42.backend.room_common.example.notification;

import ru.team42.backend.room_common.context.RoomContext;
import ru.team42.backend.room_common.example.notification.dto.ClearAllDto;
import ru.team42.backend.room_common.example.notification.dto.MarkReadDto;
import ru.team42.backend.room_common.handler.RoomHandler;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Realtime-уведомления.
 *
 * <p>Сценарий использования:
 * <ul>
 *   <li>Клиент подписывается на {@code /topic/notifications/{userId}} — получает историю непрочитанных.
 *   <li>Сервер вызывает {@link #push} — все онлайн-участники комнаты получают {@code NOTIFICATION}.
 *   <li>Клиент отправляет {@code MARK_READ} — уведомление помечается прочитанным.
 *   <li>Клиент отправляет {@code CLEAR_ALL} — история очищается.
 * </ul>
 *
 * <p>Типичный roomId = userId, чтобы каждый пользователь имел свою изолированную комнату.
 */
// @Component  ← раскомментировать для активации
public class NotificationRoom extends RoomHandler<NotificationRoomState> {

    public NotificationRoom() {
        super("notifications");
        on("MARK_READ", MarkReadDto.class, this::markRead);
        on("CLEAR_ALL", ClearAllDto.class,  this::clearAll);
    }

    @Override
    public NotificationRoomState initialState() {
        return new NotificationRoomState();
    }

    @Override
    public void onConnect(RoomContext ctx) {
        List<Notification> unread = ctx.<NotificationRoomState>state().getUnread();
        ctx.sendTo(ctx.session().getSessionId(), "INITIAL_STATE", Map.of(
                "notifications", unread,
                "unreadCount",   unread.size()
        ));
    }

    /**
     * Отправляет уведомление всем подключённым участникам и сохраняет в состоянии.
     * Вызывается из бизнес-логики или другого обработчика события.
     */
    public void push(RoomContext ctx, String title, String body) {
        Notification notification = new Notification(
                UUID.randomUUID().toString(), title, body, Instant.now());
        ctx.<NotificationRoomState>state().add(notification);
        ctx.broadcast("NOTIFICATION", notification);
    }

    private void markRead(RoomContext ctx, MarkReadDto dto) {
        boolean changed = ctx.<NotificationRoomState>state().markRead(dto.getNotificationId());
        if (changed) {
            ctx.broadcast("NOTIFICATION_READ", Map.of("id", dto.getNotificationId()));
        }
    }

    private void clearAll(RoomContext ctx, ClearAllDto dto) {
        ctx.<NotificationRoomState>state().clearAll();
        ctx.broadcast("ALL_CLEARED", Map.of());
    }
}
