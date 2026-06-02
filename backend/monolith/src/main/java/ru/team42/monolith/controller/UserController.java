package ru.team42.monolith.controller;

import org.springframework.web.bind.annotation.RequestMapping;
import ru.team42.monolith.dto.UserInfoResponse;
import ru.team42.monolith.security.AuthUserPrincipal;
import ru.team42.monolith.service.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "users", description = "User profile")
@RestController
@RequiredArgsConstructor
@RequestMapping("/user")
public class UserController {

    private final UserService userService;

    @Operation(summary = "Get current authenticated user info", security = @SecurityRequirement(name = "bearer"))
    @GetMapping("/me")
    public ResponseEntity<UserInfoResponse> me(@AuthenticationPrincipal AuthUserPrincipal userDetails) {
        return ResponseEntity.ok(userService.getByUsername(userDetails));
    }
}
