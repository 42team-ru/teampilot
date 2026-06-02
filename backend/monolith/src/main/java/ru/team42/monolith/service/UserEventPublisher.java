package ru.team42.monolith.service;

import org.springframework.stereotype.Component;
import ru.team42.backend.kafka_common.AbstractEventPublisher;
import ru.team42.backend.kafka_common.event.KafkaTopics;
import ru.team42.monolith.entity.User;

import java.util.List;

@Component
public class UserEventPublisher extends AbstractEventPublisher {

}
