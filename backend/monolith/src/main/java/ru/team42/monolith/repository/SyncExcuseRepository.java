package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.monolith.entity.SyncExcuse;

import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

public interface SyncExcuseRepository extends JpaRepository<SyncExcuse, UUID> {

    boolean existsByTelegramIdAndTeamIdAndExcuseDate(Long telegramId, UUID teamId, LocalDate date);

    List<SyncExcuse> findByTeamIdAndExcuseDate(UUID teamId, LocalDate date);

    @Transactional
    void deleteByTeamIdAndExcuseDate(UUID teamId, LocalDate date);
}
