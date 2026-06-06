package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.UserProfile;

import java.util.Optional;
import java.util.UUID;

public interface UserProfileRepository extends JpaRepository<UserProfile, UUID> {

    Optional<UserProfile> findByUserTelegramId(Long telegramId);

    Optional<UserProfile> findByUserId(UUID userId);
}
