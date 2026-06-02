package ru.team42.backend.room_common.example.casino;

import lombok.Data;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

@Data
public class CasinoRoomState {

    public enum Status { WAITING, COUNTDOWN, PLAYING, FINISHED }

    private Status status = Status.WAITING;
    private final Map<String, Player> players = new HashMap<>();
    private Instant startedAt;
    private int countdown;

    @Data
    public static class Player {
        private final String participantId;
        private String username;
        private int balance;
        private boolean ready;
    }
}
