package ru.team42.backend.room_common.example.poll.dto;

import lombok.Data;

import java.util.List;

@Data
public class CreatePollDto {
    private String question;
    private List<String> options;
}
