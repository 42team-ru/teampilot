package ru.team42.monolith.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.common_data.entity.AbstractEntity;

@Entity
@Table(name = "yougile_companies")
@Getter
@Setter
@NoArgsConstructor
public class YouGileCompany extends AbstractEntity {

    @Column(name = "yougile_company_id")
    private String yougileCompanyId;

    @Column(name = "name")
    private String name;
}
