package ru.team42.monolith.dto.response;

import ru.team42.monolith.entity.enums.TeamRole;

import java.util.UUID;

public record TeamMemberResponse(
        UUID id,
        Long telegramId,
        String telegramLogin,
        String firstName,
        String lastName,
        TeamRole role
) {}
