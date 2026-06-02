package ru.team42.backend.room_common.context;

import ru.team42.backend.room_common.model.RoomSession;

import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ScheduledFuture;

/**
 * API available to event handlers inside a room.
 * All methods are safe to call from within handler threads.
 */
/**
 * API доступен обработчикам событий внутри комнаты.
 * Все методы можно безопасно вызывать из потоков обработчика.
 */
public interface RoomContext {

    /** Сессия участника, инициировавшего это событие. */
    RoomSession session();

    /** Изменяемое состояние комнаты. Тип определяется контекстом обработчика. */
    <S> S state();

    /** Все участники, подключенные в данный момент, отсортированы по sessionId. */
    Map<String, RoomSession> participants();

    /** Трансляция(сообщение) для всех участников этой комнаты. */
    void broadcast(String event, Object payload);

    /**
     * Отправить личное сообщение конкретному участнику.
     * Цель должна быть подписана на /user/queue/events.
     */
    void sendTo(String targetSessionId, String event, Object payload);

    /**
     * Запланируйте одноразовую задачу. Она выполняется внутри последовательного исполнителя комнаты,
     * поэтому безопасно изменять состояние из него.
     */
    ScheduledFuture<?> schedule(Duration delay, Runnable task);

    /**
     * Планирует повторяющуюся задачу. Также выполняется в последовательном исполнителе комнаты.
     */
    ScheduledFuture<?> scheduleAtFixedRate(Duration period, Runnable task);

    /** Отключить всех участников и уничтожить этот экземпляр комнаты. */
    void closeRoom();
}
