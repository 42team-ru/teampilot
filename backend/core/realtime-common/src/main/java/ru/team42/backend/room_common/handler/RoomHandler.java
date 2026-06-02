package ru.team42.backend.room_common.handler;

import lombok.extern.slf4j.Slf4j;
import ru.team42.backend.room_common.context.RoomContext;
import ru.team42.backend.room_common.event.EventDescriptor;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.function.BiConsumer;

/**

 * Базовый класс для всех комнат реального времени.
 *
 * <p>Создайте подкласс, вызовите {@link #on} в конструкторе для регистрации событий,
 * затем переопределите хуки жизненного цикла по мере необходимости. Объявите подкласс как
 * Spring {@code @Component} — фреймворк автоматически его распознает.
 *
 * <pre>{@code
 * @Component
 * public class ChatRoom extends RoomHandler<ChatState> {
 * public ChatRoom() {
 * super("chat");
 * on("MESSAGE", MessageDto.class, this::onMessage);
 * }
 * protected ChatState initialState() { return new ChatState(); }
 * private void onMessage(RoomContext ctx, MessageDto dto) { ... }
 * }
 * }</pre>
 *
 * @param <S> тип состояния комнаты
 */
@Slf4j
public abstract class RoomHandler<S> {

    private final String roomType;
    private final List<EventDescriptor<?>> descriptors = new ArrayList<>();

    protected RoomHandler(String roomType) {
        this.roomType = roomType;
    }

    /** Возвращает новый объект состояния для каждого нового экземпляра комнаты. */
    public abstract S initialState();

    /** Вызывается, когда участник подписывается на тему обсуждения в комнате. */
    public void onConnect(RoomContext ctx) {}

    /** Вызывается при отключении участника. */
    public void onDisconnect(RoomContext ctx) {}

    /** Вызывается при необработанных исключениях в обработчиках событий или хуках жизненного цикла. */
    public void onError(RoomContext ctx, Exception e) {
        log.error("[room={}] unhandled error for session={}", roomType, ctx.session().getSessionId(), e);
    }

    /**
     * Регистрирует типизированный обработчик событий.
     *
     * @param event имя события во входящем пакете
     * @param payloadType класс для десериализации полезной нагрузки
     * @param handler получает контекст комнаты и десериализованную полезную нагрузку
     */
    protected <T> void on(String event, Class<T> payloadType, BiConsumer<RoomContext, T> handler) {
        descriptors.add(new EventDescriptor<>(event, payloadType, handler));
    }

    public String getRoomType() { return roomType; }

    public List<EventDescriptor<?>> getDescriptors() { return Collections.unmodifiableList(descriptors); }
}
