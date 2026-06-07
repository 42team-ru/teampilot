package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import ru.team42.monolith.entity.NotificationLog;

import java.time.Instant;
import java.util.UUID;

public interface NotificationLogRepository extends JpaRepository<NotificationLog, UUID> {

    @Query("""
            SELECT COUNT(DISTINCT n.batchId)
            FROM NotificationLog n
            WHERE n.task.id = :taskId
              AND n.type = :type
              AND n.sentAt >= :since
            """)
    long countReminderBatchesSince(
            @Param("taskId") UUID taskId,
            @Param("type") String type,
            @Param("since") Instant since
    );
}
