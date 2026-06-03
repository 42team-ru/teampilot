package ru.team42.monolith.rest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.dto.response.UserResponse;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.service.UserService;

import java.util.List;

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
                        .orElseThrow(() -> AppException.notFound("User with telegramId %d not found".formatted(telegramId)))
        );
    }

    @Operation(summary = "Список пользователей по роли")
    @GetMapping
    public ResponseEntity<List<UserResponse>> listByRole(@RequestParam String role) {
        User.Role parsed;
        try {
            parsed = User.Role.valueOf(role);
        } catch (IllegalArgumentException e) {
            throw AppException.badRequest("Unknown role: " + role);
        }
        return ResponseUtils.ok(userService.listByRole(parsed));
    }
}
