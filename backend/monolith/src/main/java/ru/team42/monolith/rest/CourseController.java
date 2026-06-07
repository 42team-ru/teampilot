package ru.team42.monolith.rest;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.dto.request.AddCourseRequest;
import ru.team42.monolith.dto.response.CourseResponse;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.service.CourseService;

import java.util.List;
import java.util.UUID;

import static ru.team42.monolith.security.RestSecurityErrorHandler.AUTH_FAILURE_DETAIL_ATTRIBUTE;

@RestController
@RequestMapping("/courses")
@RequiredArgsConstructor
@Slf4j
public class CourseController {

    private final CourseService courseService;

    @PostMapping("/teams/{teamId}/courses")
    public ResponseEntity<CourseResponse> addCourse(
            @AuthenticationPrincipal User currentUser,
            HttpServletRequest servletRequest,
            @PathVariable UUID teamId,
            @Valid @RequestBody AddCourseRequest request
    ) {
        Long telegramId = requireTelegramId(currentUser, servletRequest);
        CourseResponse response = courseService.addCourse(teamId, request.url(), telegramId);
        return ResponseUtils.created("/courses/teams/" + teamId + "/courses/" + response.id(), response);
    }

    @GetMapping("/teams/{teamId}/courses")
    public ResponseEntity<List<CourseResponse>> listCourses(
            @AuthenticationPrincipal User currentUser,
            HttpServletRequest servletRequest,
            @PathVariable UUID teamId
    ) {
        Long telegramId = requireTelegramId(currentUser, servletRequest);
        return ResponseUtils.ok(courseService.listCourses(teamId, telegramId));
    }

    private Long requireTelegramId(User currentUser, HttpServletRequest servletRequest) {
        if (currentUser == null) {
            Object failureDetail = servletRequest.getAttribute(AUTH_FAILURE_DETAIL_ATTRIBUTE);
            if (failureDetail instanceof String detail && !detail.isBlank()) {
                if (detail.startsWith("User with Telegram ID")) {
                    throw AppException.notFound(detail);
                }
                throw AppException.unauthorized(detail);
            }
            throw AppException.unauthorized(
                    "Telegram user authentication required: provide a valid X-Telegram-Id header"
            );
        }
        return currentUser.getTelegramId();
    }
}
