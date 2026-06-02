package ru.team42.backend.room_common.example.casino;

import lombok.extern.slf4j.Slf4j;
import ru.team42.backend.room_common.context.RoomContext;
import ru.team42.backend.room_common.example.casino.dto.DepositDto;
import ru.team42.backend.room_common.example.casino.dto.JoinDto;
import ru.team42.backend.room_common.example.casino.dto.ReadyDto;
import ru.team42.backend.room_common.handler.RoomHandler;
import ru.team42.backend.room_common.model.RoomSession;

import java.time.Duration;
import java.util.Map;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Example casino room demonstrating the framework.
 *
 * Flow:
 *   CONNECT  → player connects
 *   JOIN     → player sets username, appears in room
 *   DEPOSIT  → player adds balance
 *   READY    → marks player as ready; when all ready, starts countdown
 *   (auto)   → COUNTDOWN 5..1, then GAME_START
 *   (auto)   → after 10 s, GAME_RESULT + room closed
 *
 * Clients subscribe to:  /topic/casino/{roomId}
 * Clients send to:       /app/casino/{roomId}
 * Personal messages on:  /user/queue/events
 */
@Slf4j
// Uncomment to activate: @Component
public class CasinoRoom extends RoomHandler<CasinoRoomState> {

    private static final int COUNTDOWN_SECONDS = 5;
    private static final int GAME_DURATION_SECONDS = 10;
    private static final int MIN_PLAYERS = 2;

    private final AtomicReference<ScheduledFuture<?>> countdownTask = new AtomicReference<>();

    public CasinoRoom() {
        super("casino");

        on("JOIN",    JoinDto.class,    this::join);
        on("DEPOSIT", DepositDto.class, this::deposit);
        on("READY",   ReadyDto.class,   this::ready);
    }

    @Override
    public CasinoRoomState initialState() {
        return new CasinoRoomState();
    }

    // -------------------------------------------------------------------------

    @Override
    public void onConnect(RoomContext ctx) {
        RoomSession session = ctx.session();
        log.info("[casino] connect participantId={}", session.getParticipantId());
        ctx.sendTo(session.getSessionId(), "WELCOME",
                Map.of("participantId", session.getParticipantId(),
                       "playerCount", ctx.participants().size()));
    }

    @Override
    public void onDisconnect(RoomContext ctx) {
        CasinoRoomState state = ctx.state();
        state.getPlayers().remove(ctx.session().getParticipantId());
        ctx.broadcast("PLAYER_LEFT", Map.of(
                "participantId", ctx.session().getParticipantId(),
                "remaining", ctx.participants().size() - 1
        ));
    }

    // -------------------------------------------------------------------------

    private void join(RoomContext ctx, JoinDto dto) {
        CasinoRoomState state = ctx.state();

        if (state.getStatus() != CasinoRoomState.Status.WAITING) {
            ctx.sendTo(ctx.session().getSessionId(), "ERROR",
                    Map.of("message", "Game already in progress"));
            return;
        }

        CasinoRoomState.Player player = new CasinoRoomState.Player(ctx.session().getParticipantId());
        player.setUsername(dto.getUsername());
        player.setBalance(0);
        state.getPlayers().put(player.getParticipantId(), player);

        ctx.broadcast("PLAYER_JOINED", Map.of(
                "participantId", player.getParticipantId(),
                "username", player.getUsername()
        ));
    }

    private void deposit(RoomContext ctx, DepositDto dto) {
        CasinoRoomState state = ctx.state();
        CasinoRoomState.Player player = state.getPlayers().get(ctx.session().getParticipantId());
        if (player == null) {
            ctx.sendTo(ctx.session().getSessionId(), "ERROR", Map.of("message", "Join first"));
            return;
        }

        player.setBalance(player.getBalance() + dto.getAmount());
        ctx.broadcast("BALANCE_UPDATED", Map.of(
                "participantId", player.getParticipantId(),
                "balance", player.getBalance()
        ));
    }

    private void ready(RoomContext ctx, ReadyDto dto) {
        CasinoRoomState state = ctx.state();
        CasinoRoomState.Player player = state.getPlayers().get(ctx.session().getParticipantId());
        if (player == null) return;

        player.setReady(dto.isReady());
        ctx.broadcast("PLAYER_READY", Map.of(
                "participantId", player.getParticipantId(),
                "ready", dto.isReady()
        ));

        long readyCount = state.getPlayers().values().stream().filter(CasinoRoomState.Player::isReady).count();
        boolean allReady = readyCount == state.getPlayers().size()
                           && state.getPlayers().size() >= MIN_PLAYERS;

        if (allReady && state.getStatus() == CasinoRoomState.Status.WAITING) {
            startCountdown(ctx);
        }
    }

    // -------------------------------------------------------------------------

    private void startCountdown(RoomContext ctx) {
        CasinoRoomState state = ctx.state();
        state.setStatus(CasinoRoomState.Status.COUNTDOWN);
        state.setCountdown(COUNTDOWN_SECONDS);

        ctx.broadcast("COUNTDOWN_START", Map.of("seconds", COUNTDOWN_SECONDS));

        ScheduledFuture<?> task = ctx.scheduleAtFixedRate(Duration.ofSeconds(1), () -> {
            CasinoRoomState s = ctx.state();
            s.setCountdown(s.getCountdown() - 1);
            ctx.broadcast("COUNTDOWN_TICK", Map.of("remaining", s.getCountdown()));

            if (s.getCountdown() <= 0) {
                cancelCountdown();
                startGame(ctx);
            }
        });

        countdownTask.set(task);
    }

    private void cancelCountdown() {
        ScheduledFuture<?> task = countdownTask.getAndSet(null);
        if (task != null) task.cancel(false);
    }

    private void startGame(RoomContext ctx) {
        CasinoRoomState state = ctx.state();
        state.setStatus(CasinoRoomState.Status.PLAYING);
        state.setStartedAt(java.time.Instant.now());

        ctx.broadcast("GAME_START", Map.of("startedAt", state.getStartedAt().toString()));

        ctx.schedule(Duration.ofSeconds(GAME_DURATION_SECONDS), () -> finishGame(ctx));
    }

    private void finishGame(RoomContext ctx) {
        CasinoRoomState state = ctx.state();
        state.setStatus(CasinoRoomState.Status.FINISHED);

        // determine winner by highest balance
        state.getPlayers().values().stream()
             .max(java.util.Comparator.comparingInt(CasinoRoomState.Player::getBalance))
             .ifPresent(winner -> ctx.broadcast("GAME_RESULT", Map.of(
                     "winner", winner.getParticipantId(),
                     "username", winner.getUsername(),
                     "balance", winner.getBalance()
             )));

        ctx.closeRoom();
    }
}
