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
@Table(name = "meetings")
@Getter
@Setter
@NoArgsConstructor
public class Meeting extends AbstractEntity {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "team_id", nullable = false)
    private Team team;

    @Column(name = "meeting_url", nullable = false, length = 1024)
    private String meetingUrl;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "primary_recorder_id", nullable = false)
    private TeamUser primaryRecorder;

    @Column(name = "active", nullable = false)
    private boolean active = true;
}
