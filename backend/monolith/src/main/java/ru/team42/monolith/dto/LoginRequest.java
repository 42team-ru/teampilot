package ru.team42.monolith.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Schema(name = "LoginRequest", description = "Login with username and password")
@Data
public class LoginRequest {

    @Schema(description = "Username", example = "john_doe")
    @NotBlank(message = "Username is required")
    private String username;

    @Schema(description = "Password", example = "secure_password_123")
    @NotBlank(message = "Password is required")
    private String password;

    @Schema(description = "Device type: determines token delivery method", example = "WEB")
    private DeviceType deviceType = DeviceType.MOBILE;
}
