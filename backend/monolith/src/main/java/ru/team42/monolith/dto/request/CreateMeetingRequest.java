package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.util.UUID;

public record CreateMeetingRequest(
        @NotNull UUID teamId,
        @NotBlank @Size(max = 1024) String meetingUrl
) {
}
