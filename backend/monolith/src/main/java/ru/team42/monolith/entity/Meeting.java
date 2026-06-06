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

import java.time.Instant;

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

    @Column(name = "recording_bucket")
    private String recordingBucket;

    @Column(name = "recording_s3_key", length = 1024)
    private String recordingS3Key;

    @Column(name = "recording_content_type")
    private String recordingContentType;

    @Column(name = "recording_size_bytes")
    private Long recordingSizeBytes;

    @Column(name = "transcript_bucket")
    private String transcriptBucket;

    @Column(name = "transcript_s3_key", length = 1024)
    private String transcriptS3Key;

    @Column(name = "title", length = 500)
    private String title;

    @Column(name = "description", length = 2000)
    private String description;

    @Column(name = "summary", columnDefinition = "TEXT")
    private String summary;

    @Column(name = "finalized_at")
    private Instant finalizedAt;
}
