package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.dto.request.CreateInviteRequest;
import ru.team42.monolith.dto.request.LoginRequest;
import ru.team42.monolith.dto.response.AuthResponse;
import ru.team42.monolith.dto.response.InviteResponse;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.entity.enums.TeamRole;
import ru.team42.monolith.repository.TeamRepository;
import ru.team42.monolith.repository.TeamUserRepository;
import ru.team42.monolith.repository.UserRepository;

import java.util.UUID;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final TeamRepository teamRepository;
    private final TeamUserRepository teamUserRepository;
    private final UserRepository userRepository;

    @Transactional(readOnly = true)
    public InviteResponse createInvite(CreateInviteRequest request) {
        Team team = teamRepository.findByTelegramChatId(request.chatId())
                .orElseThrow(() -> AppException.notFound("Team for chatId %d not found".formatted(request.chatId())));
        return new InviteResponse(team.getId());
    }

    @Transactional
    public AuthResponse joinTeam(UUID teamId, LoginRequest request) {
        Team team = teamRepository.findById(teamId)
                .orElseThrow(() -> AppException.notFound("Team %s not found".formatted(teamId)));

        User user = userRepository.findByTelegramId(request.telegramId())
                .orElseGet(() -> createUser(request));

        // Backfill profile fields from invite if missing on user
        if (inviteToken.getFirstName() != null && user.getFirstName() == null) {
            user.setFirstName(inviteToken.getFirstName());
        }
        if (inviteToken.getLastName() != null && user.getLastName() == null) {
            user.setLastName(inviteToken.getLastName());
        }
        userRepository.save(user);

        if (!alreadyMember) {
            TeamUser teamUser = new TeamUser();
            teamUser.setTeam(team);
            teamUser.setUser(user);
            teamUser.setRole(TeamRole.USER);
            teamUserRepository.save(teamUser);
        }

        return new AuthResponse(user.getId(), user.getTelegramId(), user.getSystemRole());
    }

    private User createUser(LoginRequest request) {
        User user = new User();
        user.setTelegramId(request.telegramId());
        user.setTelegramLogin(request.telegramLogin());
        user.setFirstName(request.firstName());
        user.setLastName(request.lastName());
        return userRepository.save(user);
    }
}
