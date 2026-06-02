package ru.team42.monolith.rest;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.config.AppProperties;
import ru.team42.monolith.dto.request.CreateInviteRequest;
import ru.team42.monolith.dto.request.LoginRequest;
import ru.team42.monolith.dto.responce.AuthResponse;
import ru.team42.monolith.dto.responce.InviteResponse;
import ru.team42.monolith.service.AuthService;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;
    private final AppProperties appProperties;

    @PostMapping("/invite")
    public ResponseEntity<InviteResponse> createInvite(
            @RequestHeader("X-Bot-Secret") String botSecret,
            @RequestBody(required = false) CreateInviteRequest request
    ) {
        if (!appProperties.getBot().getSecret().equals(botSecret)) {
            throw AppException.forbidden("Invalid bot secret");
        }
        return ResponseEntity.ok(authService.createInvite(request));
    }

    @PostMapping("/login")
    public ResponseEntity<AuthResponse> login(@Valid @RequestBody LoginRequest request) {
        return ResponseEntity.ok(authService.activateInvite(request));
    }
}
