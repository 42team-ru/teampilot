package ru.team42.backend.room_common.example.auction.dto;

import lombok.Data;

@Data
public class OpenLotDto {
    private String title;
    private int startingPrice;
    /** Длительность аукциона в секундах. */
    private int durationSeconds;
}
