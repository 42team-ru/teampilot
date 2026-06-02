package ru.team42.backend.web_common.dto;

import io.swagger.v3.oas.annotations.media.Schema;

import java.util.List;

@Schema(description = "Validation error response (RFC 7807)")
public record ValidationErrorResponse(

        @Schema(description = "HTTP status code", example = "400")
        int status,

        @Schema(description = "Short error name", example = "Validation Error")
        String title,

        @Schema(description = "Detailed error description", example = "Request validation failed")
        String detail,

        @Schema(description = "Request path that caused the error", example = "/register")
        String instance,

        @Schema(description = "Trace ID for log correlation", example = "64f1a2b3c4d5e6f7")
        String traceId,

        @Schema(description = "List of field-level validation violations")
        List<FieldViolation> violations
) {}
