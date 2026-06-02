package ru.team42.backend.web_common.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "Error response")
public record ErrorResponse(

        @Schema(description = "HTTP status code", example = "404")
        int status,

        @Schema(description = "Short error name", example = "Not Found")
        String title,

        @Schema(description = "Detailed error description", example = "User abc123 not found")
        String detail,

        @Schema(description = "Request path that caused the error", example = "/api/users/abc123")
        String instance,

        @Schema(description = "Trace ID for log correlation", example = "64f1a2b3c4d5e6f7")
        String traceId
) {}
