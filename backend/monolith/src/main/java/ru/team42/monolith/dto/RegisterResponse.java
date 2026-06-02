package ru.team42.monolith.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Builder;
import lombok.Data;

@Schema(name = "RegisterResponse", description = "Successful registration response")
@Data
@Builder
public class RegisterResponse {

    @Schema(description = "UUID of the newly created user", example = "123e4567-e89b-12d3-a456-426614174000")
    private String id;

    @Schema(description = "Username", example = "john_doe")
    private String username;

    @Schema(description = "Email address", example = "john@example.com")
    private String email;
}
