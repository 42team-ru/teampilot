package ru.team42.monolith.config;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.repository.UserRepository;

@Slf4j
@Component
@RequiredArgsConstructor
public class DataSeeder implements ApplicationRunner {

    private final UserRepository userRepository;

    @Override
    public void run(ApplicationArguments args) {
        seedUser(1L, "seed_admin", "Seed Admin", User.Role.SYSTEM_ADMIN);
        seedUser(2L, "seed_user", "Seed User", User.Role.USER);
    }

    private void seedUser(Long telegramId, String login, String firstName, User.Role role) {
        if (userRepository.findByTelegramId(telegramId).isPresent()) {
            return;
        }
        User user = new User();
        user.setTelegramId(telegramId);
        user.setTelegramLogin(login);
        user.setFirstName(firstName);
        user.setRole(role);
        userRepository.save(user);
        log.info("Seeded user: {} ({})", login, role);
    }
}
