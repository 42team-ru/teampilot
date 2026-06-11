package ru.team42.monolith.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.common_data.entity.AbstractEntity;

import java.time.LocalDate;
import java.util.UUID;

@Entity
@Table(name = "sick_leave_records")
@Getter
@Setter
@NoArgsConstructor
public class SickLeaveRecord extends AbstractEntity {

    @Column(name = "telegram_id", nullable = false)
    private Long telegramId;

    @Column(name = "team_id", nullable = false)
    private UUID teamId;

    @Column(name = "reason")
    private String reason;

    @Column(name = "record_date", nullable = false)
    private LocalDate recordDate;
}
