package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.NotNull;
import ru.team42.monolith.entity.enums.TeamRole;

public record UpdateMemberRoleRequest(@NotNull TeamRole role) {}
