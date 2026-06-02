package ru.team42.monolith.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(name = "MessageResponse", description = "Plain text response")
public record MessageResponse(

        @Schema(description = "Message", example = "Logged out successfully")
        String message
) {
}
