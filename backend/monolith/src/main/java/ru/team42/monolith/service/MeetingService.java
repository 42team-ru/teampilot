package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.dto.request.CreateMeetingRequest;
import ru.team42.monolith.dto.response.MeetingResponse;
import ru.team42.monolith.entity.Meeting;
import ru.team42.monolith.entity.MeetingSpeakerMapping;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.entity.enums.TeamRole;
import ru.team42.monolith.event.MeetingLiveResultEvent;
import ru.team42.monolith.repository.MeetingRepository;
import ru.team42.monolith.repository.MeetingSpeakerMappingRepository;
import ru.team42.monolith.repository.TeamUserRepository;

import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class MeetingService {

    private final MeetingRepository meetingRepository;
    private final TeamService teamService;
    private final NotificationEventPublisher notificationEventPublisher;
    private final TeamUserRepository teamUserRepository;
    private final MeetingSpeakerMappingRepository meetingSpeakerMappingRepository;

    @Transactional
    public MeetingResponse create(CreateMeetingRequest request, Long managerTelegramId) {
        var managerMembership = teamService.requireManagerMembership(request.teamId(), managerTelegramId);

        var meeting = new Meeting();
        meeting.setTeam(managerMembership.getTeam());
        meeting.setMeetingUrl(request.meetingUrl());
        meeting.setPrimaryRecorder(managerMembership);
        meeting.setActive(true);

        return MeetingResponse.from(meetingRepository.save(meeting));
    }

    @Transactional(readOnly = true)
    public MeetingResponse getByMeetingUrl(String meetingUrl) {
        return meetingRepository.findFirstByMeetingUrlAndActiveTrueOrderByCreatedAtDesc(meetingUrl)
                .map(MeetingResponse::from)
                .orElseThrow(() -> AppException.notFound(
                        "Менеджер ещё не прикрепил этот митинг к команде. Попросите менеджера создать митинг для этой команды."
                ));
    }

    @Transactional(readOnly = true)
    public Meeting getActiveMeeting(UUID meetingId) {
        return meetingRepository.findById(meetingId)
                .filter(Meeting::isActive)
                .orElseThrow(() -> AppException.notFound("Active meeting with ID %s not found".formatted(meetingId)));
    }

    @Transactional
    public void updateFinalResult(MeetingLiveResultEvent event) {
        var meetingId = UUID.fromString(event.getMeetingId());
        var meeting = meetingRepository.findById(meetingId)
                .orElseThrow(() -> AppException.notFound("Meeting with ID %s not found".formatted(meetingId)));

        meeting.setRecordingBucket(event.getRecordingBucket());
        meeting.setRecordingS3Key(event.getRecordingS3Key());
        meeting.setRecordingContentType(event.getRecordingContentType());
        meeting.setRecordingSizeBytes(event.getRecordingSizeBytes());
        meeting.setTranscriptBucket(event.getTranscriptBucket());
        meeting.setTranscriptS3Key(event.getTranscriptS3Key());
        meeting.setTitle(event.getTitle());
        meeting.setDescription(event.getDescription());
        meeting.setSummary(event.getSummary());
        meeting.setFinalizedAt(event.getFinalizedAt());

        if (meeting.getTelegramSummarySentAt() == null
                && event.getSummary() != null
                && !event.getSummary().isBlank()) {
            meeting.setTelegramSummarySentAt(java.time.Instant.now());
            notificationEventPublisher.publishMeetingSummary(meeting, event);
        }
    }

    @Transactional(readOnly = true)
    public List<SpeakerCandidate> getSpeakerCandidates(UUID meetingId, Long managerTelegramId) {
        Meeting meeting = requireMeetingManager(meetingId, managerTelegramId);
        return teamUserRepository.findByTeamIdWithUser(meeting.getTeam().getId())
                .stream()
                .filter(member -> member.getUser() != null && member.getUser().getTelegramId() != null)
                .map(member -> new SpeakerCandidate(
                        member.getUser().getTelegramId(),
                        member.getUser().getTelegramLogin(),
                        fullName(member),
                        member.getRole().name()
                ))
                .toList();
    }

    @Transactional
    public SpeakerMappingResult mapSpeaker(
            UUID meetingId,
            String speakerLabel,
            Long participantTelegramId,
            Long managerTelegramId
    ) {
        Meeting meeting = requireMeetingManager(meetingId, managerTelegramId);
        if (speakerLabel == null || speakerLabel.isBlank()) {
            throw AppException.badRequest("speakerLabel is required");
        }

        TeamUser participant = null;
        if (participantTelegramId != null && participantTelegramId != 0) {
            participant = teamUserRepository.findByTeamIdAndUserTelegramId(meeting.getTeam().getId(), participantTelegramId)
                    .orElseThrow(() -> AppException.notFound("Participant not found in meeting team"));
        }

        MeetingSpeakerMapping mapping = meetingSpeakerMappingRepository
                .findByMeetingIdAndSpeakerLabel(meetingId, speakerLabel)
                .orElseGet(MeetingSpeakerMapping::new);
        mapping.setMeeting(meeting);
        mapping.setSpeakerLabel(speakerLabel);
        mapping.setTeamUser(participant);
        mapping.setMappedByTelegramId(managerTelegramId);
        meetingSpeakerMappingRepository.save(mapping);

        String displayName = participant != null ? displayName(participant) : "Гость";
        Long mappedTelegramId = participant != null ? participant.getUser().getTelegramId() : null;
        return new SpeakerMappingResult(speakerLabel, mappedTelegramId, displayName);
    }

    private Meeting requireMeetingManager(UUID meetingId, Long telegramId) {
        if (telegramId == null) {
            throw AppException.unauthorized("Telegram user authentication required");
        }
        Meeting meeting = meetingRepository.findById(meetingId)
                .orElseThrow(() -> AppException.notFound("Meeting with ID %s not found".formatted(meetingId)));
        teamUserRepository.findByTeamIdAndUserTelegramId(meeting.getTeam().getId(), telegramId)
                .filter(member -> member.getRole() == TeamRole.MANAGER)
                .orElseThrow(() -> AppException.forbidden("Only team managers can map meeting speakers"));
        return meeting;
    }

    private String fullName(TeamUser member) {
        var user = member.getUser();
        String first = user.getFirstName() != null ? user.getFirstName().trim() : "";
        String last = user.getLastName() != null ? user.getLastName().trim() : "";
        return (first + " " + last).trim();
    }

    private String displayName(TeamUser member) {
        var user = member.getUser();
        if (user.getTelegramLogin() != null && !user.getTelegramLogin().isBlank()) {
            return "@" + user.getTelegramLogin();
        }
        String name = fullName(member);
        return !name.isBlank() ? name : user.getTelegramId().toString();
    }

    public record SpeakerCandidate(
            Long telegramId,
            String username,
            String fullName,
            String role
    ) {}

    public record SpeakerMappingResult(
            String speakerLabel,
            Long telegramId,
            String displayName
    ) {}
}
