package ru.team42.monolith.kafka.consumer;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.dto.response.MeetingLiveResultResponse;
import ru.team42.monolith.event.MeetingLiveResultEvent;
import ru.team42.monolith.service.MeetingService;

@Slf4j
@Component
@RequiredArgsConstructor
public class MeetingLiveResultConsumer {

    private final SimpMessagingTemplate messagingTemplate;
    private final MeetingService meetingService;

    @KafkaListener(topics = KafkaTopics.MEETINGS_LIVE_RESULTS)
    public void consume(MeetingLiveResultEvent event) {
        log.info("Received meeting live result meetingId={} chunkIndex={}",
                event.getMeetingId(), event.getChunkIndex());
        if (event.isFinalResult()) {
            try {
                meetingService.updateFinalResult(event);
            } catch (Exception e) {
                log.error("Failed to update final meeting result meetingId={}: {}",
                        event.getMeetingId(), e.getMessage(), e);
            }
        }
        messagingTemplate.convertAndSend(
                "/topic/meetings/%s/results".formatted(event.getMeetingId()),
                MeetingLiveResultResponse.from(event)
        );
    }
}
