package ru.team42.monolith.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.common_data.entity.AbstractEntity;

@Entity
@Table(name = "task_status_history")
@Getter
@Setter
@NoArgsConstructor
public class TaskStatusHistory extends AbstractEntity {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "task_id", nullable = false)
    private Task task;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "from_column_id")
    private TaskColumn fromColumn;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "to_column_id")
    private TaskColumn toColumn;

    /** Telegram user ID of whoever triggered the change (null = system/LLM) */
    @Column(name = "changed_by_telegram_id")
    private Long changedByTelegramId;
}
