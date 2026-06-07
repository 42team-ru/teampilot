package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public record UpdateYouGileProfileRequest(
        @NotNull Long telegramId,
        @NotBlank String yougileLogin,
        @NotBlank String yougilePassword
) {}
