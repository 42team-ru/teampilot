package ru.team42.backend.kafka_common.event;

import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.util.List;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class UserCreatedEvent extends BaseEvent {
    private String userId;
    private String username;
    private String email;
    private List<String> roles;
}