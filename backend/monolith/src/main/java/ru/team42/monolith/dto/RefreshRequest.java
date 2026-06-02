package ru.team42.monolith.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Schema(
        name = "RefreshRequest",
        description = "Access token refresh request. For WEB clients the token is read from cookie automatically."
)
@Data
public class RefreshRequest {

    @Schema(
            description = "Refresh token UUID. WEB: sent via HTTP-only cookie. MOBILE: sent in the request body.",
            example = "550e8400-e29b-41d4-a716-446655440000"
    )
    private String refreshToken;
}
