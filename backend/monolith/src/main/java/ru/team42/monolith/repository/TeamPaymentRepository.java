package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.TeamPayment;

import java.util.Optional;
import java.util.UUID;

public interface TeamPaymentRepository extends JpaRepository<TeamPayment, UUID> {

    Optional<TeamPayment> findByYookassaPaymentId(String yookassaPaymentId);
}
