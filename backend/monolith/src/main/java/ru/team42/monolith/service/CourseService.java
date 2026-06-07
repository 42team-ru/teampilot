package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.dto.response.CourseResponse;
import ru.team42.monolith.entity.Course;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.entity.enums.CourseScope;
import ru.team42.monolith.entity.enums.TeamRole;
import ru.team42.monolith.repository.CourseRepository;
import ru.team42.monolith.repository.TeamRepository;
import ru.team42.monolith.repository.TeamUserRepository;

import java.io.IOException;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class CourseService {

    private final CourseRepository courseRepository;
    private final TeamRepository teamRepository;
    private final TeamUserRepository teamUserRepository;
    private final CourseEventPublisher courseEventPublisher;

    @Transactional
    public CourseResponse addCourse(UUID teamId, String url, Long requesterTelegramId) {
        TeamUser teamUser = teamUserRepository.findByTeamIdAndUserTelegramId(teamId, requesterTelegramId)
                .orElseThrow(() -> AppException.forbidden("You are not a member of this team"));

        if (teamUser.getRole() != TeamRole.MANAGER) {
            throw AppException.forbidden("Only managers can add courses");
        }

        String normalizedUrl = normalizeUrl(url);

        Team team = teamRepository.findById(teamId)
                .orElseThrow(() -> AppException.notFound("Team %s not found".formatted(teamId)));

        String title = normalizedUrl;
        String description = null;
        String thumbnailUrl = null;

        try {
            Document doc = Jsoup.connect(normalizedUrl).timeout(5000)
                    .userAgent("Mozilla/5.0")
                    .get();
            String ogTitle = doc.select("meta[property=og:title]").attr("content");
            String ogDescription = doc.select("meta[property=og:description]").attr("content");
            String ogImage = doc.select("meta[property=og:image]").attr("content");

            if (!ogTitle.isBlank()) {
                title = ogTitle.trim();
            } else {
                String docTitle = doc.title();
                if (!docTitle.isBlank()) {
                    title = docTitle.trim();
                }
            }
            if (!ogDescription.isBlank()) {
                description = ogDescription.trim();
            }
            if (!ogImage.isBlank()) {
                thumbnailUrl = ogImage.trim();
            }
        } catch (IOException e) {
            log.warn("Could not fetch og:meta from URL {}: {}", normalizedUrl, e.getMessage());
        }

        Course course = new Course();
        course.setUrl(normalizedUrl);
        course.setTitle(title);
        course.setDescription(description);
        course.setThumbnailUrl(thumbnailUrl);
        course.setScope(CourseScope.TEAM);
        course.setTeam(team);

        Course saved = courseRepository.save(course);
        courseEventPublisher.publishCourseIndexed(saved);

        return CourseResponse.from(saved);
    }

    @Transactional(readOnly = true)
    public List<CourseResponse> listCourses(UUID teamId, Long requesterTelegramId) {
        teamUserRepository.findByTeamIdAndUserTelegramId(teamId, requesterTelegramId)
                .orElseThrow(() -> AppException.forbidden("You are not a member of this team"));

        List<Course> teamCourses = courseRepository.findByTeamId(teamId);
        List<Course> globalCourses = courseRepository.findByScope(CourseScope.GLOBAL);

        List<Course> all = new ArrayList<>(teamCourses.size() + globalCourses.size());
        all.addAll(teamCourses);
        all.addAll(globalCourses);

        return all.stream().map(CourseResponse::from).toList();
    }

    private String normalizeUrl(String raw) {
        if (raw == null || raw.isBlank()) {
            throw AppException.badRequest("URL must not be blank");
        }
        String url = raw.trim();
        if (url.length() > 2048) {
            throw AppException.badRequest("URL is too long");
        }
        try {
            URI uri = new URI(url);
            String scheme = uri.getScheme();
            if (!"http".equals(scheme) && !"https".equals(scheme)) {
                throw AppException.badRequest("URL must start with http:// or https://");
            }
            if (uri.getHost() == null || uri.getHost().isBlank()) {
                throw AppException.badRequest("URL has no host");
            }
        } catch (URISyntaxException e) {
            throw AppException.badRequest("Invalid URL: " + e.getMessage());
        }
        return url;
    }
}
