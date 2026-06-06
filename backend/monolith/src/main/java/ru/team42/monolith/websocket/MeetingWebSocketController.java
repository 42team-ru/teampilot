package ru.team42.monolith.websocket;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.messaging.handler.annotation.DestinationVariable;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.security.core.Authentication;
import org.springframework.stereotype.Controller;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.dto.request.MeetingAudioChunkRequest;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.service.MeetingAudioChunkService;

import java.security.Principal;
import java.util.UUID;

@Controller
@RequiredArgsConstructor
public class MeetingWebSocketController {

    private final MeetingAudioChunkService meetingAudioChunkService;

    @MessageMapping("/meetings/{meetingId}/chunks")
    public void acceptChunk(
            @DestinationVariable UUID meetingId,
            @Valid @Payload MeetingAudioChunkRequest request,
            Principal principal
    ) {
        meetingAudioChunkService.acceptChunk(meetingId, request, requireUser(principal));
    }

    private User requireUser(Principal principal) {
        if (principal instanceof Authentication authentication
                && authentication.getPrincipal() instanceof User user) {
            return user;
        }
        throw AppException.unauthorized("Authenticated WebSocket user required");
    }
}
