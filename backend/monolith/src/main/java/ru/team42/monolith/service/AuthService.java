package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.config.AppProperties;
import ru.team42.monolith.dto.request.CreateInviteRequest;
import ru.team42.monolith.dto.request.LoginRequest;
import ru.team42.monolith.dto.response.AuthResponse;
import ru.team42.monolith.dto.response.InviteResponse;
import ru.team42.monolith.entity.InviteToken;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.repository.InviteTokenRepository;
import ru.team42.monolith.repository.UserRepository;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final InviteTokenRepository inviteTokenRepository;
    private final UserRepository userRepository;
    private final AppProperties appProperties;

    @Transactional
    public InviteResponse createInvite(CreateInviteRequest request) {
        String token = "inv_" + UUID.randomUUID().toString().replace("-", "").substring(0, 8);

        Instant expiresAt = Instant.now().plus(
                appProperties.getInvite().getExpirationDays(), ChronoUnit.DAYS
        );

        InviteToken inviteToken = new InviteToken();
        inviteToken.setToken(token);
        inviteToken.setExpiresAt(expiresAt);
        inviteToken.setCreatedBy(request != null ? request.createdBy() : null);
        inviteTokenRepository.save(inviteToken);

        String inviteUrl = appProperties.getInvite().getBotUrl() + "?start=" + token;
        return new InviteResponse(token, expiresAt, inviteUrl);
    }

    @Transactional
    public AuthResponse activateInvite(LoginRequest request) {
        InviteToken inviteToken = inviteTokenRepository.findByToken(request.inviteToken())
                .orElseThrow(() -> AppException.notFound("Invite token not found"));

        if (inviteToken.getUsedAt() != null) {
            throw AppException.alreadyExists("Invite token already used");
        }
        if (inviteToken.getExpiresAt().isBefore(Instant.now())) {
            throw AppException.badRequest("Invite token expired");
        }

        User user = userRepository.findByTelegramId(request.telegramId())
                .orElseGet(() -> createUser(request));

        inviteToken.setUsedAt(Instant.now());
        inviteToken.setUsedByUser(user);
        inviteTokenRepository.save(inviteToken);

        return new AuthResponse(user.getId(), user.getTelegramId(), user.getRole());
    }

    private User createUser(LoginRequest request) {
        User user = new User();
        user.setTelegramId(request.telegramId());
        user.setTelegramLogin(request.telegramLogin());
        user.setFirstName(request.firstName());
        user.setLastName(request.lastName());
        User saved = userRepository.save(user);
        return saved;
    }
}
