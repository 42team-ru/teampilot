package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.YouGileCompany;

import java.util.UUID;

public interface YouGileCompanyRepository extends JpaRepository<YouGileCompany, UUID> {
}
