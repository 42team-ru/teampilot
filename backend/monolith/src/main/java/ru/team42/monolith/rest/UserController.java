package ru.team42.monolith.rest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import io.swagger.v3.oas.annotations.Parameter;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.dto.request.UpdateUserRequest;
import ru.team42.monolith.dto.response.UserResponse;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.entity.enums.SystemRole;
import ru.team42.monolith.service.UserService;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/users")
@RequiredArgsConstructor
@Tag(name = "Users", description = "Управление пользователями")
public class UserController {

    private final UserService userService;

    @Operation(summary = "Получить пользователя по Telegram ID")
    @GetMapping("/{telegramId}")
    public ResponseEntity<UserResponse> getByTelegramId(@PathVariable Long telegramId) {
        return ResponseUtils.ok(
                userService.findByTelegramId(telegramId)
                        .orElseThrow(() -> AppException.notFound(
                                "User with Telegram ID %d not found".formatted(telegramId)
                        ))
        );
    }

    @Operation(summary = "Обновить имя и фамилию текущего пользователя")
    @PreAuthorize("isAuthenticated()")
    @PatchMapping("/me")
    public ResponseEntity<UserResponse> updateMe(
            @Parameter(hidden = true) @AuthenticationPrincipal User currentUser,
            @Valid @RequestBody UpdateUserRequest request
    ) {
        return ResponseUtils.ok(userService.update(currentUser.getId(), request));
    }

    @Operation(summary = "Обновить имя и фамилию пользователя (только бот, системный админ или сам пользователь)")
    @PreAuthorize("hasRole('BOT') or hasRole('SYSTEM_ADMIN') or authentication.principal.id == #id")
    @PatchMapping("/{id}")
    public ResponseEntity<UserResponse> update(
            @PathVariable UUID id,
            @Valid @RequestBody UpdateUserRequest request
    ) {
        return ResponseUtils.ok(userService.update(id, request));
    }

    @Operation(summary = "Список пользователей по роли")
    @GetMapping
    public ResponseEntity<List<UserResponse>> listByRole(@RequestParam String role) {
        SystemRole parsed;
        try {
            parsed = SystemRole.valueOf(role);
        } catch (IllegalArgumentException e) {
            throw AppException.badRequest("Unknown role: " + role);
        }
        return ResponseUtils.ok(userService.listByRole(parsed));
    }

}
