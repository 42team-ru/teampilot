package ru.team42.monolith.event;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.extern.jackson.Jacksonized;
import ru.team42.backend.kafka_common.event.BaseEvent;

import java.time.Instant;
import java.util.List;

@Getter
@Builder
@Jacksonized
@AllArgsConstructor
@NoArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class MeetingLiveResultEvent extends BaseEvent {

    private String meetingId;
    private String teamId;
    private Integer chunkIndex;
    private String transcript;
    private String summary;
    private String context;
    private boolean finalResult;
    private String title;
    private String description;
    private String recordingBucket;
    private String recordingS3Key;
    private String recordingContentType;
    private Long recordingSizeBytes;
    private String transcriptBucket;
    private String transcriptS3Key;
    private Instant finalizedAt;

    @Builder.Default
    private List<TaskDto> tasks = List.of();
    @Builder.Default
    private List<StatusDto> statuses = List.of();

    @Getter
    @Builder
    @Jacksonized
    @AllArgsConstructor
    @NoArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class TaskDto {
        private String title;
        private String description;
        private Long assigneeId;
        private String deadline;
        private String columnId;
        private float confidence;
    }

    @Getter
    @Builder
    @Jacksonized
    @AllArgsConstructor
    @NoArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class StatusDto {
        private String taskId;
        private Long assigneeId;
        private String columnId;
        private String action;
    }
}
