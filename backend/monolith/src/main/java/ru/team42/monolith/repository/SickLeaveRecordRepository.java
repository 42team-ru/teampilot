package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.SickLeaveRecord;

import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

public interface SickLeaveRecordRepository extends JpaRepository<SickLeaveRecord, UUID> {

    List<SickLeaveRecord> findByTeamId(UUID teamId);

    List<SickLeaveRecord> findByTeamIdAndRecordDateGreaterThanEqual(UUID teamId, LocalDate from);

    boolean existsByTeamIdAndTelegramIdAndRecordDate(UUID teamId, Long telegramId, LocalDate recordDate);
}
