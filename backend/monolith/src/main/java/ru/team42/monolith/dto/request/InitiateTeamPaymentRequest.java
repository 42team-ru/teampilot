package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record InitiateTeamPaymentRequest(
        @NotBlank @Size(min = 2, max = 100) String teamName
) {}
