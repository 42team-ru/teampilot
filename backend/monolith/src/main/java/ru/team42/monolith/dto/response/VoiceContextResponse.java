package ru.team42.monolith.dto.response;

import java.util.List;

/** Единый контекст доски для голосового агента: участники, колонки, сводка.
 * Отдаётся одним запросом, чтобы агент не дёргал несколько эндпоинтов. */
public record VoiceContextResponse(
        List<VoiceMemberResponse> members,
        List<String> columns,
        TaskStatsResponse stats
) {
}
