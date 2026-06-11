package ru.team42.monolith.dto.response;

import java.util.Map;

/**
 * Счётчики доски команды для голосовых ответов ассистента.
 * byColumn — карта «название колонки → количество активных задач» (беклог, в работе, …),
 * так как набор колодок канбана у каждой команды свой.
 */
public record TaskStatsResponse(
        long total,
        long completed,
        long overdue,
        long dueToday,
        long dueTomorrow,
        Map<String, Long> byColumn
) {
}
