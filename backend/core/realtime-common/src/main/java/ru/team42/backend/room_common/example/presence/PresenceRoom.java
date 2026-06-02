package ru.team42.backend.room_common.example.presence;

import ru.team42.backend.room_common.context.RoomContext;
import ru.team42.backend.room_common.example.presence.dto.UpdatePresenceDto;
import ru.team42.backend.room_common.handler.RoomHandler;

import java.time.Instant;
import java.util.Map;

/**
 * Комната присутствия — онлайн-статусы и курсоры участников.
 *
 * <p>Подходит для: collaborative-редакторов, shared-воркспейсов, отображения «кто онлайн».
 *
 * <p>Поток событий:
 * <pre>
 * CONNECT   → новый участник получает снимок всех присутствий,
 *             остальные получают USER_JOINED
 * UPDATE    → обновить свой статус / позицию курсора →  broadcast PRESENCE_UPDATE
 * DISCONNECT→ broadcast USER_LEFT
 * </pre>
 *
 * <p>Клиент подписывается на: {@code /topic/presence/{workspaceId}}
 */
// @Component
public class PresenceRoom extends RoomHandler<PresenceRoomState> {

    public PresenceRoom() {
        super("presence");
        on("UPDATE", UpdatePresenceDto.class, this::update);
    }

    @Override
    public PresenceRoomState initialState() {
        return new PresenceRoomState();
    }

    @Override
    public void onConnect(RoomContext ctx) {
        PresenceRoomState state = ctx.state();
        String pid = ctx.session().getParticipantId();

        PresenceInfo info = state.getOrCreate(pid);

        // снимок всех присутствий — только новому участнику
        ctx.sendTo(ctx.session().getSessionId(), "PRESENCE_SNAPSHOT",
                Map.of("presences", state.getAll()));

        // остальные узнают о новом участнике
        ctx.broadcast("USER_JOINED", Map.of(
                "participantId", pid,
                "presence",      info
        ));
    }

    @Override
    public void onDisconnect(RoomContext ctx) {
        String pid = ctx.session().getParticipantId();
        ctx.<PresenceRoomState>state().remove(pid);
        ctx.broadcast("USER_LEFT", Map.of("participantId", pid));
    }

    private void update(RoomContext ctx, UpdatePresenceDto dto) {
        PresenceRoomState state = ctx.state();
        String pid = ctx.session().getParticipantId();
        PresenceInfo info = state.getOrCreate(pid);

        if (dto.getDisplayName() != null) info.setDisplayName(dto.getDisplayName());
        if (dto.getStatus()      != null) info.setStatus(dto.getStatus());
        if (dto.getCursorX()     != null) info.setCursorX(dto.getCursorX());
        if (dto.getCursorY()     != null) info.setCursorY(dto.getCursorY());
        info.setLastSeenAt(Instant.now());

        ctx.broadcast("PRESENCE_UPDATE", Map.of(
                "participantId", pid,
                "presence",      info
        ));
    }
}
