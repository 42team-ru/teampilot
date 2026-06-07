package ru.team42.monolith.dto.response;

import ru.team42.monolith.entity.Course;

import java.time.LocalDateTime;
import java.util.UUID;

public record CourseResponse(
        UUID id,
        String url,
        String title,
        String description,
        String thumbnailUrl,
        String scope,
        LocalDateTime createdAt
) {
    public static CourseResponse from(Course course) {
        return new CourseResponse(
                course.getId(),
                course.getUrl(),
                course.getTitle(),
                course.getDescription(),
                course.getThumbnailUrl(),
                course.getScope().name(),
                course.getCreatedAt()
        );
    }
}
