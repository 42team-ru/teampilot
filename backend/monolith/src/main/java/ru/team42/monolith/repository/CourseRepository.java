package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.Course;
import ru.team42.monolith.entity.enums.CourseScope;

import java.util.List;
import java.util.UUID;

public interface CourseRepository extends JpaRepository<Course, UUID> {

    List<Course> findByTeamId(UUID teamId);

    List<Course> findByScope(CourseScope scope);

    boolean existsByUrl(String url);

    List<Course> findByIdIn(List<UUID> ids);
}
