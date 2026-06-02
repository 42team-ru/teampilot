package ru.team42.backend.web_common.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "Validation violation for a single field")
public record FieldViolation(

        @Schema(description = "Field name", example = "email")
        String field,

        @Schema(description = "Error message", example = "Invalid email format")
        String message
) {}
