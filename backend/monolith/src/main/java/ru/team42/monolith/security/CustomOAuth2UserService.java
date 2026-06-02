package ru.team42.monolith.security;

import ru.team42.monolith.entity.User;
import ru.team42.monolith.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.client.userinfo.DefaultOAuth2UserService;
import org.springframework.security.oauth2.client.userinfo.OAuth2UserRequest;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class CustomOAuth2UserService extends DefaultOAuth2UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @Override
    public OAuth2User loadUser(OAuth2UserRequest userRequest) throws OAuth2AuthenticationException {
        OAuth2User oAuth2User = super.loadUser(userRequest);
        String registrationId = userRequest.getClientRegistration().getRegistrationId();

        UserInfo userInfo = extractUserInfo(registrationId, oAuth2User);

        User user = userRepository.findByEmailOrUsername(userInfo.email(), userInfo.username())
                .map(existing -> updateExistingUser(existing, userInfo))
                .orElseGet(() -> createNewUser(userInfo));

        return AuthUserPrincipal.ofOAuth2(user, oAuth2User.getAttributes());
    }

    private UserInfo extractUserInfo(String registrationId, OAuth2User oAuth2User) {
        return switch (registrationId) {
            case "yandex" -> {
                String login = oAuth2User.getAttribute("login");
                String email = oAuth2User.getAttribute("default_email");
                String firstName = oAuth2User.getAttribute("first_name");
                String lastName = oAuth2User.getAttribute("last_name");
                yield new UserInfo(
                        login != null ? login : email,
                        email,
                        firstName != null ? firstName : login,
                        lastName != null ? lastName : "",
                        User.AuthProvider.YANDEX
                );
            }
            case "github" -> {
                String login = oAuth2User.getAttribute("login");
                String email = oAuth2User.getAttribute("email");
                if (email == null || email.isBlank()) {
                    email = login + "@users.noreply.github.com";
                }
                String firstName = login;
                String lastName = "";
                String fullName = oAuth2User.getAttribute("name");
                if (fullName != null && !fullName.isBlank()) {
                    int space = fullName.indexOf(' ');
                    if (space > 0) {
                        firstName = fullName.substring(0, space);
                        lastName = fullName.substring(space + 1);
                    } else {
                        firstName = fullName;
                    }
                }
                yield new UserInfo(login, email, firstName, lastName, User.AuthProvider.GITHUB);
            }
            default -> throw new OAuth2AuthenticationException("Неподдерживаемый OAuth2 провайдер: " + registrationId);
        };
    }

    private record UserInfo(String username, String email, String firstName, String lastName, User.AuthProvider provider) {}

    private User updateExistingUser(User existing, UserInfo info) {
        existing.setFirstName(info.firstName());
        existing.setLastName(info.lastName());
        existing.setAuthProvider(info.provider());
        return userRepository.save(existing);
    }

    private User createNewUser(UserInfo info) {
        User user = User.builder()
                .username(info.username())
                .email(info.email())
                .passwordHash(passwordEncoder.encode(UUID.randomUUID().toString()))
                .active(true)
                .emailVerified(true)
                .roles(List.of(User.UserRole.USER))
                .authProvider(info.provider())
                .firstName(info.firstName())
                .lastName(info.lastName())
                .build();
        return userRepository.save(user);
    }
}
