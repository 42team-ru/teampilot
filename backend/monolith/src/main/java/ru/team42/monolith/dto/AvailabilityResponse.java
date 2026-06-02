package ru.team42.monolith.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(name = "AvailabilityResponse", description = "Username or email availability check result")
public record AvailabilityResponse(

        @Schema(description = "true if the value is available, false if already taken", example = "true")
        boolean available
) {
}
