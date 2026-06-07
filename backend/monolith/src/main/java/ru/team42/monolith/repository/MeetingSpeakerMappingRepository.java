package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.MeetingSpeakerMapping;

import java.util.Optional;
import java.util.UUID;

public interface MeetingSpeakerMappingRepository extends JpaRepository<MeetingSpeakerMapping, UUID> {

    Optional<MeetingSpeakerMapping> findByMeetingIdAndSpeakerLabel(UUID meetingId, String speakerLabel);
}
