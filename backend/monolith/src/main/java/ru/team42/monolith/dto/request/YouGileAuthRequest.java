package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record YouGileAuthRequest(
        @NotNull Long chatId,
        @NotBlank String login,
        @NotBlank String password,
        String companyId   // null → auto-select if 1 company, else return list
) {}
