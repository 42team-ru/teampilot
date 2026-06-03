package ru.team42.monolith.dto.request;

import com.fasterxml.jackson.annotation.JsonInclude;

@JsonInclude(JsonInclude.Include.NON_NULL)
public record AdminCreateTeamRequest(
        Long telegramChatId,
        String chatTitle,
        String kanbanId,        // optional — can be set later
        String kanbanApiKey,    // optional — can be set later
        Long adminTelegramId,
        String adminUsername
) {}
