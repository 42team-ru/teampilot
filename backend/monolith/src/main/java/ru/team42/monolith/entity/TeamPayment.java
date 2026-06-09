package ru.team42.monolith.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.common_data.entity.AbstractEntity;
import ru.team42.monolith.entity.enums.TeamPaymentStatus;

@Entity
@Table(name = "team_payments")
@Getter
@Setter
@NoArgsConstructor
public class TeamPayment extends AbstractEntity {

    @Column(name = "yookassa_payment_id", unique = true)
    private String yookassaPaymentId;

    @Column(name = "telegram_id", nullable = false)
    private Long telegramId;

    @Column(name = "team_name", nullable = false)
    private String teamName;

    @Enumerated(EnumType.STRING)
    @Column(name = "status", nullable = false)
    private TeamPaymentStatus status = TeamPaymentStatus.PENDING;
}
