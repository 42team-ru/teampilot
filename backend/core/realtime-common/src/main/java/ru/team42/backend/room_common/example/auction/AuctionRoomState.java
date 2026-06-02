package ru.team42.backend.room_common.example.auction;

import lombok.Data;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

@Data
public class AuctionRoomState {

    public enum Status { WAITING, ACTIVE, CLOSED }

    @Data
    public static class BidRecord {
        private final String participantId;
        private final int amount;
        private final Instant placedAt;
    }

    private Status status = Status.WAITING;
    private String lotTitle;
    private int currentPrice;
    private String leaderId;    // participantId текущего лидера
    private Instant endsAt;
    private final List<BidRecord> bids = new ArrayList<>();
}
