package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.dto.response.UserResponse;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.repository.UserRepository;

import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class UserService {

    private final UserRepository userRepository;

    public Optional<UserResponse> findByTelegramId(Long telegramId) {
        return userRepository.findByTelegramId(telegramId)
                .map(this::toResponse);
    }

    public List<UserResponse> listByRole(User.Role role) {
        return userRepository.findAllByRole(role).stream()
                .map(this::toResponse)
                .toList();
    }

    @Transactional
    public void linkToYougile(Long telegramId, String yougileUserId, String yougileDisplayName) {
        User user = userRepository.findByTelegramId(telegramId)
                .orElseThrow(() -> AppException.notFound("User with telegramId %d not found".formatted(telegramId)));
        user.setYougileUserId(yougileUserId);
        user.setYougileDisplayName(yougileDisplayName);
        userRepository.save(user);
    }

    private UserResponse toResponse(User user) {
        return new UserResponse(
                user.getId(),
                user.getTelegramId(),
                user.getRole().name(),
                user.getFirstName(),
                user.getLastName(),
                user.getPosition(),
                user.getTelegramLogin(),
                user.getYougileUserId() != null,
                user.getYougileDisplayName()
        );
    }
}
