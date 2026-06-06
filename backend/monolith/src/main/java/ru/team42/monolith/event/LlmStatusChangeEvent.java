package ru.team42.monolith.event;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.*;
import lombok.extern.jackson.Jacksonized;
import ru.team42.backend.kafka_common.event.BaseEvent;

@Getter
@Builder
@Jacksonized
@AllArgsConstructor
@NoArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class LlmStatusChangeEvent extends BaseEvent {

    private String teamId;

    /** UUID задачи, выбранный LLM из RAG-кандидатов — может быть null если не совпало */
    private String taskId;

    /** telegram_id исполнителя — может быть null */
    private Long assigneeId;

    /** ID колонки канбана, выбранный LLM — может быть null */
    private String columnId;

    /** COMPLETE | ASSIGN | CANCEL */
    private String action;

    private String sourceBatchId;
}
