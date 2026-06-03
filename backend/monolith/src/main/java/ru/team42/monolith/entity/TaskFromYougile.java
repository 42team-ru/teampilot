package ru.team42.monolith.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.common_data.entity.AbstractEntity;
import ru.team42.monolith.entity.enums.TaskLocalStatus;

@Entity
@Table(name = "tasks_from_yougile")
@Getter
@Setter
@NoArgsConstructor
public class TaskFromYougile extends AbstractEntity {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "team_id", nullable = false)
    private Team team;

    @Column(name = "yougile_id", nullable = false)
    private String yougileId;

    @Column(name = "name", nullable = false)
    private String name;

    @Column(name = "description", columnDefinition = "TEXT")
    private String description;

    @Enumerated(EnumType.STRING)
    @Column(name = "local_status", nullable = false, length = 30)
    private TaskLocalStatus localStatus = TaskLocalStatus.ACTIVE;

    // Raw status string from YouGile (column name / status label) - возможно нужно жестко захардкодить
    @Column(name = "yougile_status")
    private String yougileStatus;
}
