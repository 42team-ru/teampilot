package ru.team42.monolith.controller;

import ru.team42.monolith.service.AuthService;
import ru.team42.monolith.service.UserService;
import ru.team42.monolith.dto.*;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import ru.team42.backend.web_common.dto.ErrorResponse;
import ru.team42.backend.web_common.dto.ValidationErrorResponse;

@Tag(name = "auth", description = "Authentication and registration")
@RestController
@RequiredArgsConstructor
@RequestMapping("/auth")
public class AuthController {

    private final AuthService authService;
    private final UserService userService;

    @Operation(summary = "Log in with username and password")
    @ApiResponse(responseCode = "200", description = "Login successful")
    @ApiResponse(responseCode = "400", description = "Invalid request data",
            content = @Content(schema = @Schema(implementation = ValidationErrorResponse.class)))
    @ApiResponse(responseCode = "401", description = "Bad credentials",
            content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
    @PostMapping("/login")
    public ResponseEntity<TokenResponse> login(@Valid @RequestBody LoginRequest req,
                                               HttpServletResponse response,
                                               HttpServletRequest request) {
        return ResponseEntity.ok(authService.login(req, response, request));
    }

    @Operation(summary = "Register a new user")
    @ApiResponse(responseCode = "201", description = "User created")
    @ApiResponse(responseCode = "400", description = "Invalid request data",
            content = @Content(schema = @Schema(implementation = ValidationErrorResponse.class)))
    @ApiResponse(responseCode = "409", description = "Email or username already taken",
            content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
    @PostMapping("/register")
    public ResponseEntity<RegisterResponse> register(@Valid @RequestBody RegisterRequest dto) {
        return ResponseEntity.status(HttpStatus.CREATED).body(authService.register(dto));
    }

    @Operation(summary = "Refresh the access token")
    @ApiResponse(responseCode = "200", description = "Token refreshed")
    @ApiResponse(responseCode = "401", description = "Refresh token not found or expired",
            content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
    @PostMapping("/refresh")
    public ResponseEntity<TokenResponse> refresh(
            @RequestBody(required = false) RefreshRequest body,
            HttpServletRequest request,
            HttpServletResponse response) {
        return ResponseEntity.ok(authService.refresh(body, request, response));
    }

    @Operation(summary = "Log out and revoke the refresh token")
    @ApiResponse(responseCode = "200", description = "Logged out successfully")
    @PostMapping("/logout")
    public ResponseEntity<MessageResponse> logout(
            @RequestBody(required = false) RefreshRequest body,
            HttpServletRequest request,
            HttpServletResponse response) {
        return ResponseEntity.ok(authService.logout(body, request, response));
    }

    @Operation(summary = "Check email availability")
    @GetMapping("/check/email")
    public ResponseEntity<AvailabilityResponse> checkEmail(@RequestParam String email) {
        return ResponseEntity.ok(new AvailabilityResponse(userService.isEmailAvailable(email)));
    }

    @Operation(summary = "Check username availability")
    @GetMapping("/check/username")
    public ResponseEntity<AvailabilityResponse> checkUsername(@RequestParam String username) {
        return ResponseEntity.ok(new AvailabilityResponse(userService.isUsernameAvailable(username)));
    }
}
