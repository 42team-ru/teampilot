package ru.team42.backend.kafka_common.event;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.Map;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class UserUpdatedEvent extends BaseEvent {
    private String userId;
    private Map<String, String> updatedFields;
}