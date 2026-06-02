package ru.team42.monolith.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Builder;
import lombok.Data;

import java.util.List;

@Schema(name = "TokenResponse", description = "Successful authentication response with tokens and user info")
@Data
@Builder
@JsonInclude(JsonInclude.Include.NON_NULL)
public class TokenResponse {

    @Schema(description = "RSA-signed JWT access token (TTL: 15 min)", example = "eyJhbGciOiJSUzI1NiJ9...")
    private String accessToken;

    @Schema(description = "Refresh token UUID (TTL: 30 days). WEB: set in HTTP-only cookie.", example = "550e8400-e29b-41d4-a716-446655440000")
    private String refreshToken;

    @Schema(description = "Access token lifetime in seconds", example = "900")
    private Long expiresIn;

    @Schema(description = "Token type", example = "Bearer")
    private String tokenType;

    @Schema(description = "User UUID", example = "123e4567-e89b-12d3-a456-426614174000")
    private String userId;

    @Schema(description = "Username", example = "john_doe")
    private String username;

    @Schema(description = "Email address", example = "john@example.com")
    private String email;

    @Schema(description = "First name", example = "John")
    private String firstName;

    @Schema(description = "Last name", example = "Doe")
    private String lastName;

    @Schema(description = "User roles", example = "[\"ROLE_USER\"]")
    private List<String> roles;
}
