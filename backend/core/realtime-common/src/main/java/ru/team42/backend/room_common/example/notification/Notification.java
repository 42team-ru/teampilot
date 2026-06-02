package ru.team42.backend.room_common.example.notification;

import lombok.AllArgsConstructor;
import lombok.Data;

import java.time.Instant;

@Data
@AllArgsConstructor
public class Notification {
    private String id;
    private String title;
    private String body;
    private boolean read;
    private Instant createdAt;

    public Notification(String id, String title, String body, Instant createdAt) {
        this(id, title, body, false, createdAt);
    }
}
