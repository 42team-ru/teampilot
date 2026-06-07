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
        name = "meeting_speaker_mappings",
        uniqueConstraints = @UniqueConstraint(name = "uk_meeting_speaker_label", columnNames = {"meeting_id", "speaker_label"})
)
@Getter
@Setter
@NoArgsConstructor
public class MeetingSpeakerMapping extends AbstractEntity {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "meeting_id", nullable = false)
    private Meeting meeting;

    @Column(name = "speaker_label", nullable = false, length = 40)
    private String speakerLabel;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "team_user_id")
    private TeamUser teamUser;

    @Column(name = "mapped_by_telegram_id")
    private Long mappedByTelegramId;
}
