package ru.team42.monolith.event;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.*;
import lombok.extern.jackson.Jacksonized;
import ru.team42.backend.kafka_common.event.BaseEvent;

import java.util.List;

@Getter
@Builder
@Jacksonized
@AllArgsConstructor
@NoArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class SyncDraftEvent extends BaseEvent {

    private String requestId;
    private String teamId;
    private Long telegramUserId;
    private List<DraftItem> items;

    @Getter
    @Builder
    @Jacksonized
    @AllArgsConstructor
    @NoArgsConstructor
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class DraftItem {
        private int index;
        private String userText;
        /** null если задача не найдена в YouGile */
        private String taskId;
        private String taskTitle;
        private boolean isNewTask;
        private Long assigneeTelegramId;
        private String assigneeName;
    }
}
