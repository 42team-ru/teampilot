package ru.team42.backend.room_common.example.casino;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import ru.team42.backend.room_common.context.RoomContext;
import ru.team42.backend.room_common.example.casino.dto.DepositDto;
import ru.team42.backend.room_common.example.casino.dto.JoinDto;
import ru.team42.backend.room_common.example.casino.dto.ReadyDto;
import ru.team42.backend.room_common.support.TestRoom;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("CasinoRoom")
class CasinoRoomTest {

    private CasinoRoom casino;

    @BeforeEach
    void setUp() {
        casino = new CasinoRoom();
    }

    // -------------------------------------------------------------------------

    @Test
    @DisplayName("onConnect — отправляет WELCOME лично подключившемуся")
    void onConnect_sendsPersonalWelcome() {
        var room = new TestRoom<>(casino.initialState());
        var ctx = room.ctx("alice");

        casino.onConnect(ctx);

        assertThat(room.hasSentTo("alice", "WELCOME")).isTrue();
        var msg = room.sentTo("alice").getFirst();
        assertThat(msg.payload()).asString().contains("participantId");
    }

    @Test
    @DisplayName("JOIN — игрок появляется в комнате, всем приходит broadcast")
    void join_playerAppearsInRoom() {
        var room = new TestRoom<>(casino.initialState());
        var ctx = room.ctx("alice");

        room.dispatch(casino, ctx, "JOIN", join("Alice"));

        assertThat(room.hasBroadcast("PLAYER_JOINED")).isTrue();
        assertThat(room.getState().getPlayers()).containsKey("alice");
        assertThat(room.getState().getPlayers().get("alice").getUsername()).isEqualTo("Alice");
    }

    @Test
    @DisplayName("DEPOSIT — баланс увеличивается, broadcast BALANCE_UPDATED")
    void deposit_updatesBalance() {
        var room = new TestRoom<>(casino.initialState());
        var ctx = room.ctx("alice");

        room.dispatch(casino, ctx, "JOIN", join("Alice"));
        room.dispatch(casino, ctx, "DEPOSIT", deposit(150));

        assertThat(room.getState().getPlayers().get("alice").getBalance()).isEqualTo(150);
        assertThat(room.hasBroadcast("BALANCE_UPDATED")).isTrue();
    }

    @Test
    @DisplayName("READY — отсчёт начинается только когда все 2+ игрока готовы")
    void ready_countdownStartsOnlyWhenAllReady() {
        var room = new TestRoom<>(casino.initialState());
        var ctxA = room.ctx("alice");
        var ctxB = room.ctx("bob");

        room.dispatch(casino, ctxA, "JOIN", join("Alice"));
        room.dispatch(casino, ctxB, "JOIN", join("Bob"));

        // один игрок готов — отсчёт не стартует
        room.dispatch(casino, ctxA, "READY", ready());
        assertThat(room.hasBroadcast("COUNTDOWN_START")).isFalse();

        // второй готов — отсчёт запускается
        room.dispatch(casino, ctxB, "READY", ready());
        assertThat(room.hasBroadcast("COUNTDOWN_START")).isTrue();
        assertThat(room.scheduledTaskCount()).isEqualTo(1);
        assertThat(room.getState().getStatus()).isEqualTo(CasinoRoomState.Status.COUNTDOWN);
    }

    @Test
    @DisplayName("COUNTDOWN — 5 тиков приводят к GAME_START")
    void countdown_ticksToZeroAndStartsGame() {
        var room = new TestRoom<>(casino.initialState());
        setupTwoReadyPlayers(room);

        // тикаем 5 раз (COUNTDOWN_SECONDS = 5)
        for (int i = 0; i < 5; i++) room.runScheduledTask(0);

        assertThat(room.broadcastsOf("COUNTDOWN_TICK")).hasSize(5);
        assertThat(room.hasBroadcast("GAME_START")).isTrue();
        assertThat(room.getState().getStatus()).isEqualTo(CasinoRoomState.Status.PLAYING);
    }

    @Test
    @DisplayName("GAME_RESULT — победитель с максимальным балансом, комната закрывается")
    void gameFinishes_broadcastsWinnerAndClosesRoom() {
        var room = new TestRoom<>(casino.initialState());
        setupTwoReadyPlayers(room);

        // bob пополняет баланс и должен выиграть
        room.dispatch(casino, room.ctx("bob"), "DEPOSIT", deposit(300));

        // прогоняем отсчёт и дожидаемся GAME_START
        for (int i = 0; i < 5; i++) room.runScheduledTask(0);

        // прогоняем задачу завершения игры (добавляется на индекс 1)
        room.runScheduledTask(1);

        assertThat(room.hasBroadcast("GAME_RESULT")).isTrue();
        var result = room.lastBroadcast("GAME_RESULT");
        assertThat(result.payload().toString()).contains("bob");
        assertThat(room.isClosed()).isTrue();
    }

    @Test
    @DisplayName("JOIN во время игры — игрок получает ERROR, в комнату не добавляется")
    void join_whileGameInProgress_receivesError() {
        var room = new TestRoom<>(casino.initialState());
        setupTwoReadyPlayers(room);
        for (int i = 0; i < 5; i++) room.runScheduledTask(0); // start game
        room.clearBroadcasts();

        var ctx = room.ctx("charlie");
        room.dispatch(casino, ctx, "JOIN", join("Charlie"));

        assertThat(room.hasSentTo("charlie", "ERROR")).isTrue();
        assertThat(room.hasBroadcast("PLAYER_JOINED")).isFalse();
        assertThat(room.getState().getPlayers()).doesNotContainKey("charlie");
    }

    @Test
    @DisplayName("onDisconnect — участник удаляется из состояния")
    void disconnect_removesPlayer() {
        var room = new TestRoom<>(casino.initialState());
        var ctx = room.ctx("alice");

        room.dispatch(casino, ctx, "JOIN", join("Alice"));
        casino.onDisconnect(ctx);

        assertThat(room.getState().getPlayers()).doesNotContainKey("alice");
        assertThat(room.hasBroadcast("PLAYER_LEFT")).isTrue();
    }

    // -------------------------------------------------------------------------
    // helpers

    private void setupTwoReadyPlayers(TestRoom<CasinoRoomState> room) {
        var ctxA = room.ctx("alice");
        var ctxB = room.ctx("bob");
        room.dispatch(casino, ctxA, "JOIN", join("Alice"));
        room.dispatch(casino, ctxB, "JOIN", join("Bob"));
        room.dispatch(casino, ctxA, "READY", ready());
        room.dispatch(casino, ctxB, "READY", ready());
    }

    private static JoinDto join(String username) {
        var d = new JoinDto();
        d.setUsername(username);
        return d;
    }

    private static DepositDto deposit(int amount) {
        var d = new DepositDto();
        d.setAmount(amount);
        return d;
    }

    private static ReadyDto ready() {
        var d = new ReadyDto();
        d.setReady(true);
        return d;
    }
}
