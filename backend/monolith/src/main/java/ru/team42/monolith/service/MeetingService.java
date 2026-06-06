package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.dto.request.CreateMeetingRequest;
import ru.team42.monolith.dto.response.MeetingResponse;
import ru.team42.monolith.entity.Meeting;
import ru.team42.monolith.repository.MeetingRepository;

import java.util.UUID;

@Service
@RequiredArgsConstructor
public class MeetingService {

    private final MeetingRepository meetingRepository;
    private final TeamService teamService;

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
}
