package ru.team42.monolith.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.common_data.entity.AbstractEntity;

@Entity
@Table(
        name = "task_columns",
        uniqueConstraints = @UniqueConstraint(
                name = "uq_task_columns_team_yougile_id",
                columnNames = {"team_id", "yougile_column_id"}
        )
)
@Getter
@Setter
@NoArgsConstructor
public class TaskColumn extends AbstractEntity {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "team_id", nullable = false)
    private Team team;

    @Column(name = "title", nullable = false)
    private String title;

    /** ID колонки в YouGile */
    @Column(name = "yougile_column_id")
    private String youGileColumnId;

    @Column(name = "deleted", columnDefinition = "boolean not null default false")
    private boolean deleted = false;
}
