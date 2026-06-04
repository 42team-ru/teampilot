package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.dto.request.UpdateUserRequest;
import ru.team42.monolith.dto.response.UserResponse;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.entity.enums.SystemRole;
import ru.team42.monolith.repository.UserRepository;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class UserService {

    private final UserRepository userRepository;

    public Optional<UserResponse> findByTelegramId(Long telegramId) {
        return userRepository.findByTelegramId(telegramId)
                .map(this::toResponse);
    }

    @Transactional
    public UserResponse update(UUID id, UpdateUserRequest request) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> AppException.notFound("User %s not found".formatted(id)));
        if (request.firstName() != null) user.setFirstName(request.firstName());
        if (request.lastName() != null) user.setLastName(request.lastName());
        return toResponse(userRepository.save(user));
    }

    public List<UserResponse> listByRole(SystemRole systemRole) {
        return userRepository.findAllBySystemRole(systemRole).stream()
                .map(this::toResponse)
                .toList();
    }

    private UserResponse toResponse(User user) {
        return new UserResponse(
                user.getId(),
                user.getTelegramId(),
                user.getSystemRole().name(),
                user.getFirstName(),
                user.getLastName(),
                user.getTelegramLogin()
        );
    }
}
