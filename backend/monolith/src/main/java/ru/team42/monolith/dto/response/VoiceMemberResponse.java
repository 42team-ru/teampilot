package ru.team42.monolith.dto.response;

import java.util.UUID;

/** Участник команды для голосового агента: внутренний id + отображаемое имя. */
public record VoiceMemberResponse(
        UUID id,
        String name
) {
}
