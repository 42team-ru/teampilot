package ru.team42.monolith.service;

import ru.team42.monolith.dto.UserInfoResponse;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.security.AuthUserPrincipal;

import java.util.List;

@Service
@RequiredArgsConstructor
public class UserService {

    private final UserRepository userRepository;

    @Transactional(readOnly = true)
    public UserInfoResponse getByUsername(AuthUserPrincipal authUserPrincipal) {
        User user = userRepository.findByUsername(authUserPrincipal.getUsername())
                .orElseThrow(() -> AppException.notFound("Пользователь '" + authUserPrincipal.getUsername() + "' не найден"));

        List<String> roles = user.getRoles().stream()
                .map(r -> "ROLE_" + r.name())
                .toList();

        return UserInfoResponse.builder()
                .userId(user.getId().toString())
                .username(user.getUsername())
                .email(user.getEmail())
                .firstName(user.getFirstName())
                .lastName(user.getLastName())
                .roles(roles)
                .build();
    }

    @Transactional(readOnly = true)
    public boolean isEmailAvailable(String email) {
        return !userRepository.existsByEmailIgnoreCase(email);
    }

    @Transactional(readOnly = true)
    public boolean isUsernameAvailable(String username) {
        return !userRepository.existsByUsernameIgnoreCase(username);
    }
}
