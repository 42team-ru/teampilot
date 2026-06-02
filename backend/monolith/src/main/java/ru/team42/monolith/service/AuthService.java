package ru.team42.monolith.service;

import ru.team42.monolith.dto.*;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.repository.UserRepository;
import ru.team42.monolith.security.AuthUserPrincipal;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import ru.team42.backend.web_common.exception.AppException;

import java.util.List;

@Service
@Slf4j
@RequiredArgsConstructor
public class AuthService {

    private final AuthenticationManager authenticationManager;
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final TokenService tokenService;

    public TokenResponse login(LoginRequest req, HttpServletResponse response, HttpServletRequest request) {
        User user = userRepository.findByUsername(req.getUsername())
                .filter(u -> passwordEncoder.matches(req.getPassword(), u.getPasswordHash()))
                .orElseThrow(() -> AppException.unauthorized("Неверный логин или пароль"));

        DeviceType deviceType = req.getDeviceType() != null ? req.getDeviceType() : DeviceType.MOBILE;
        TokenPair tokenPair = tokenService.generateTokenPair(user);

        if (deviceType == DeviceType.WEB) {
            tokenService.setTokenCookies(response, tokenPair, request);
        }

        log.info("Успешный вход пользователя: {}", user.getUsername());
        return tokenService.buildTokenResponse(user, tokenPair, deviceType);
    }

    public RegisterResponse register(RegisterRequest dto) {
        if (userRepository.findByEmailOrUsername(dto.getEmail(), dto.getUsername()).isPresent()) {
            throw AppException.alreadyExists("Пользователь с таким логином или email уже существует");
        }

        User user = User.builder()
                .username(dto.getUsername())
                .email(dto.getEmail())
                .firstName(dto.getFirstName())
                .lastName(dto.getLastName())
                .passwordHash(passwordEncoder.encode(dto.getPassword()))
                .roles(List.of(User.UserRole.USER))
                .emailVerified(true)
                .active(true)
                .authProvider(User.AuthProvider.LOCAL)
                .build();

        User saved = userRepository.save(user);
        log.info("Зарегистрирован новый пользователь: {}", saved.getUsername());

        return RegisterResponse.builder()
                .id(saved.getId().toString())
                .username(saved.getUsername())
                .email(saved.getEmail())
                .build();
    }

    public TokenResponse refresh(RefreshRequest body, HttpServletRequest request, HttpServletResponse response) {
        String refreshToken = tokenService.extractRefreshToken(request, body);
        if (refreshToken == null || refreshToken.isBlank()) {
            throw AppException.unauthorized("Refresh token отсутствует");
        }

        String username = tokenService.validateAndRotateRefreshToken(request, response, refreshToken);
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> AppException.notFound("Пользователь не найден"));

        DeviceType deviceType = tokenService.detectDeviceType(request);
        TokenPair newTokenPair = tokenService.generateTokenPair(user);

        if (deviceType == DeviceType.WEB) {
            tokenService.setTokenCookies(response, newTokenPair, request);
        }

        log.info("Refresh token rotation для: {}", user.getUsername());
        return tokenService.buildTokenResponse(user, newTokenPair, deviceType);
    }

    public MessageResponse logout(RefreshRequest body, HttpServletRequest request, HttpServletResponse response) {
        String refreshToken = tokenService.extractRefreshToken(request, body);
        tokenService.revokeRefreshToken(refreshToken);
        tokenService.clearTokenCookies(response, request);
        return new MessageResponse("Выход выполнен");
    }
}
