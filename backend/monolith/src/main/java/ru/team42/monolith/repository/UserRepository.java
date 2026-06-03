package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.entity.enums.SystemRole;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface UserRepository extends JpaRepository<User, UUID> {
    Optional<User> findByTelegramId(Long telegramId);

    List<User> findAllBySystemRole(SystemRole systemRole);
}
