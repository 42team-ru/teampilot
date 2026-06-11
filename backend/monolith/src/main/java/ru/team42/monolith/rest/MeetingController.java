package ru.team42.monolith.rest;

import io.swagger.v3.oas.annotations.Parameter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.dto.request.CreateMeetingRequest;
import ru.team42.monolith.dto.request.MeetingAudioChunkRequest;
import ru.team42.monolith.dto.response.MeetingResponse;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.service.MeetingAudioChunkService;
import ru.team42.monolith.service.MeetingService;

import java.util.List;
import java.util.UUID;

import static ru.team42.monolith.security.RestSecurityErrorHandler.AUTH_FAILURE_DETAIL_ATTRIBUTE;

@RestController
@RequestMapping("/meetings")
@RequiredArgsConstructor
@Validated
public class MeetingController {

    private final MeetingService meetingService;
    private final MeetingAudioChunkService meetingAudioChunkService;

    @PostMapping
    public ResponseEntity<MeetingResponse> create(
            @Parameter(hidden = true) @AuthenticationPrincipal User currentUser,
            HttpServletRequest servletRequest,
            @Valid @RequestBody CreateMeetingRequest request
    ) {
        return ResponseUtils.ok(meetingService.create(request, requireTelegramId(currentUser, servletRequest)));
    }

    @PostMapping("/{meetingId}/bot-chunks")
    @PreAuthorize("hasRole('BOT')")
    public ResponseEntity<Void> acceptBotChunk(
            @PathVariable UUID meetingId,
            @Valid @RequestBody MeetingAudioChunkRequest request
    ) {
        meetingAudioChunkService.acceptBotChunk(meetingId, request);
        return ResponseUtils.noContent();
    }

    @GetMapping("/by-url")
    public ResponseEntity<MeetingResponse> getByUrl(@RequestParam @NotBlank String meetingUrl) {
        return ResponseUtils.ok(meetingService.getByMeetingUrl(meetingUrl));
    }

    @GetMapping("/{meetingId}/speaker-candidates")
    @PreAuthorize("hasRole('BOT') or hasRole('SYSTEM_ADMIN')")
    public ResponseEntity<List<MeetingService.SpeakerCandidate>> getSpeakerCandidates(
            @PathVariable UUID meetingId,
            @RequestParam Long telegramUserId
    ) {
        return ResponseUtils.ok(meetingService.getSpeakerCandidates(meetingId, telegramUserId));
    }

    @PostMapping("/{meetingId}/speaker-mappings")
    @PreAuthorize("hasRole('BOT') or hasRole('SYSTEM_ADMIN')")
    public ResponseEntity<MeetingService.SpeakerMappingResult> mapSpeaker(
            @PathVariable UUID meetingId,
            @RequestBody SpeakerMappingRequest request
    ) {
        return ResponseUtils.ok(meetingService.mapSpeaker(
                meetingId,
                request.speakerLabel(),
                request.participantTelegramId(),
                request.telegramUserId()
        ));
    }

    public record SpeakerMappingRequest(
            String speakerLabel,
            Long participantTelegramId,
            Long telegramUserId
    ) {}

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
