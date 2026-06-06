package ru.team42.monolith.kafka.consumer;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.dto.response.MeetingLiveResultResponse;
import ru.team42.monolith.event.MeetingLiveResultEvent;

@Slf4j
@Component
@RequiredArgsConstructor
public class MeetingLiveResultConsumer {

    private final SimpMessagingTemplate messagingTemplate;

    @KafkaListener(topics = KafkaTopics.MEETINGS_LIVE_RESULTS)
    public void consume(MeetingLiveResultEvent event) {
        log.info("Received meeting live result meetingId={} chunkIndex={}",
                event.getMeetingId(), event.getChunkIndex());
        messagingTemplate.convertAndSend(
                "/topic/meetings/%s/results".formatted(event.getMeetingId()),
                MeetingLiveResultResponse.from(event)
        );
    }
}
