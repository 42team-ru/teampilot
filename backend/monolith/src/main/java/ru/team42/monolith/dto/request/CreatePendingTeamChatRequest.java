package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record CreatePendingTeamChatRequest(
        @NotNull Long telegramChatId,
        @NotBlank String chatTitle
) {}
