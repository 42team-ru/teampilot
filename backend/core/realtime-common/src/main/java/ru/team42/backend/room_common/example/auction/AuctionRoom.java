package ru.team42.backend.room_common.example.auction;

import ru.team42.backend.room_common.context.RoomContext;
import ru.team42.backend.room_common.example.auction.dto.BidDto;
import ru.team42.backend.room_common.example.auction.dto.OpenLotDto;
import ru.team42.backend.room_common.handler.RoomHandler;

import java.time.Duration;
import java.time.Instant;
import java.util.Map;

/**
 * Аукционная комната.
 *
 * <p>Поток событий:
 * <pre>
 * OPEN_LOT  — открыть лот (ведущий/организатор)
 * BID       — поставить ставку (участник)
 * (auto)    → AUCTION_ENDED + WINNER / NO_WINNER после истечения таймера
 * </pre>
 *
 * <p>Клиент подписывается на: {@code /topic/auction/{lotId}}
 * <p>Клиент отправляет на:    {@code /app/auction/{lotId}}
 */
// @Component
public class AuctionRoom extends RoomHandler<AuctionRoomState> {

    public AuctionRoom() {
        super("auction");
        on("OPEN_LOT", OpenLotDto.class, this::openLot);
        on("BID",      BidDto.class,     this::bid);
    }

    @Override
    public AuctionRoomState initialState() {
        return new AuctionRoomState();
    }

    @Override
    public void onConnect(RoomContext ctx) {
        AuctionRoomState state = ctx.state();
        ctx.sendTo(ctx.session().getSessionId(), "AUCTION_STATE", Map.of(
                "status",       state.getStatus(),
                "lotTitle",     state.getLotTitle() != null ? state.getLotTitle() : "",
                "currentPrice", state.getCurrentPrice(),
                "leaderId",     state.getLeaderId() != null ? state.getLeaderId() : "",
                "bids",         state.getBids()
        ));
    }

    // -------------------------------------------------------------------------

    private void openLot(RoomContext ctx, OpenLotDto dto) {
        AuctionRoomState state = ctx.state();
        if (state.getStatus() != AuctionRoomState.Status.WAITING) {
            ctx.sendTo(ctx.session().getSessionId(), "ERROR",
                    Map.of("message", "Аукцион уже идёт или завершён"));
            return;
        }

        state.setStatus(AuctionRoomState.Status.ACTIVE);
        state.setLotTitle(dto.getTitle());
        state.setCurrentPrice(dto.getStartingPrice());
        state.setEndsAt(Instant.now().plusSeconds(dto.getDurationSeconds()));

        ctx.broadcast("LOT_OPENED", Map.of(
                "title",        dto.getTitle(),
                "startingPrice", dto.getStartingPrice(),
                "endsAt",       state.getEndsAt().toString()
        ));

        ctx.schedule(Duration.ofSeconds(dto.getDurationSeconds()), () -> closeAuction(ctx));
    }

    private void bid(RoomContext ctx, BidDto dto) {
        AuctionRoomState state = ctx.state();

        if (state.getStatus() != AuctionRoomState.Status.ACTIVE) {
            ctx.sendTo(ctx.session().getSessionId(), "ERROR",
                    Map.of("message", "Аукцион не активен"));
            return;
        }
        if (dto.getAmount() <= state.getCurrentPrice()) {
            ctx.sendTo(ctx.session().getSessionId(), "ERROR",
                    Map.of("message", "Ставка должна быть выше текущей: " + state.getCurrentPrice()));
            return;
        }

        String prevLeader = state.getLeaderId();
        state.setCurrentPrice(dto.getAmount());
        state.setLeaderId(ctx.session().getParticipantId());
        state.getBids().add(new AuctionRoomState.BidRecord(
                ctx.session().getParticipantId(), dto.getAmount(), Instant.now()));

        ctx.broadcast("NEW_BID", Map.of(
                "participantId", ctx.session().getParticipantId(),
                "amount",        dto.getAmount()
        ));

        // уведомить предыдущего лидера об обгоне
        if (prevLeader != null && !prevLeader.equals(ctx.session().getParticipantId())) {
            ctx.participants().values().stream()
                    .filter(s -> s.getParticipantId().equals(prevLeader))
                    .findFirst()
                    .ifPresent(s -> ctx.sendTo(s.getSessionId(), "OUTBID",
                            Map.of("newAmount", dto.getAmount())));
        }
    }

    private void closeAuction(RoomContext ctx) {
        AuctionRoomState state = ctx.state();
        state.setStatus(AuctionRoomState.Status.CLOSED);

        if (state.getLeaderId() != null) {
            ctx.broadcast("WINNER", Map.of(
                    "participantId", state.getLeaderId(),
                    "finalPrice",    state.getCurrentPrice()
            ));
        } else {
            ctx.broadcast("NO_WINNER", Map.of("reason", "no bids placed"));
        }

        ctx.broadcast("AUCTION_ENDED", Map.of("lotTitle", state.getLotTitle()));
        ctx.closeRoom();
    }
}
