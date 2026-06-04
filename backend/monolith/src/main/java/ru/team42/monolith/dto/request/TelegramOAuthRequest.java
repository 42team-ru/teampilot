package ru.team42.monolith.dto.request;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotNull;

public record TelegramOAuthRequest(
        @NotNull Long id,
        @JsonProperty("first_name") String firstName,
        @JsonProperty("last_name") String lastName,
        @JsonProperty("username") String username,
        @JsonProperty("photo_url") String photoUrl,
        @JsonProperty("auth_date") @NotNull Long authDate,
        @NotNull String hash
) {}
