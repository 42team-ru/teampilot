package ru.team42.backend.room_common.event;

import ru.team42.backend.room_common.context.RoomContext;

import java.util.function.BiConsumer;

/** Типизированная привязка между именем события, его классом полезной нагрузки и обработчиком. */
public final class EventDescriptor<T> {

    private final String name;
    private final Class<T> payloadType;
    private final BiConsumer<RoomContext, T> handler;

    public EventDescriptor(String name, Class<T> payloadType, BiConsumer<RoomContext, T> handler) {
        this.name = name;
        this.payloadType = payloadType;
        this.handler = handler;
    }

    public String getName() { return name; }
    public Class<T> getPayloadType() { return payloadType; }
    public BiConsumer<RoomContext, T> getHandler() { return handler; }
}
