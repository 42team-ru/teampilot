package ru.team42.monolith.config;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.entity.enums.SystemRole;
import ru.team42.monolith.repository.UserRepository;

@Slf4j
@Component
@RequiredArgsConstructor
public class DataSeeder implements ApplicationRunner {

    private final UserRepository userRepository;

    @Override
    public void run(ApplicationArguments args) {
        seedAdminUser(2031863132L, "eiiwoqodhkqoqo", "владмиир", "Мельник");
        seedAdminUser(713978344L, "idzey878", "Кирилл", "Пантюхин");
        seedAdminUser(1763162562L, "lagroDev", "василий", "Мельник");
        seedAdminUser(5288131710L, "VlaDoNS1", "Влад", "Лихолетов");
    }

    private void seedAdminUser(Long telegramId, String login, String firstName, String lastName) {
        User user = userRepository.findByTelegramId(telegramId)
                .orElseGet(User::new);

        user.setTelegramId(telegramId);
        user.setTelegramLogin(login);
        user.setFirstName(firstName);
        user.setLastName(lastName);
        user.setSystemRole(SystemRole.SYSTEM_ADMIN);

        userRepository.save(user);
        log.info("Seeded admin user: {}", login);
    }
}
