package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.UserAchievement;

import java.util.List;
import java.util.UUID;

public interface UserAchievementRepository extends JpaRepository<UserAchievement, UUID> {

    List<UserAchievement> findByUserId(UUID userId);

    List<UserAchievement> findByUserIdOrderByAwardedAtDesc(UUID userId);

    boolean existsByUserIdAndAchievementKey(UUID userId, String achievementKey);
}
