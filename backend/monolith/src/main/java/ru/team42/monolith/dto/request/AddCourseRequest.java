package ru.team42.monolith.dto.request;

import jakarta.validation.constraints.NotBlank;

public record AddCourseRequest(
        @NotBlank String url
) {
}
