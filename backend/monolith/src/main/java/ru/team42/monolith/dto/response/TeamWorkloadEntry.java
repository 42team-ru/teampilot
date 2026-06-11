package ru.team42.monolith.dto.response;

public record TeamWorkloadEntry(
    String teamUserId,
    String firstName,
    String lastName,
    String telegramLogin,
    Long telegramId,
    long openTaskCount,
    long overdueTaskCount
) {}
