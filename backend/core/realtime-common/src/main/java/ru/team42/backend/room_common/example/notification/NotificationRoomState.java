package ru.team42.backend.room_common.example.notification;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class NotificationRoomState {

    private final List<Notification> notifications = new ArrayList<>();

    public void add(Notification notification) {
        notifications.add(notification);
    }

    public List<Notification> getUnread() {
        return notifications.stream().filter(n -> !n.isRead()).toList();
    }

    public List<Notification> getAll() {
        return Collections.unmodifiableList(notifications);
    }

    public boolean markRead(String notificationId) {
        return notifications.stream()
                .filter(n -> n.getId().equals(notificationId) && !n.isRead())
                .peek(n -> n.setRead(true))
                .findFirst()
                .isPresent();
    }

    public void clearAll() {
        notifications.clear();
    }
}
