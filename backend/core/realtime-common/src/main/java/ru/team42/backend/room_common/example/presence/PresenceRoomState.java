package ru.team42.backend.room_common.example.presence;

import java.util.Collections;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class PresenceRoomState {

    /** participantId → PresenceInfo */
    private final Map<String, PresenceInfo> presences = new ConcurrentHashMap<>();

    public PresenceInfo getOrCreate(String participantId) {
        return presences.computeIfAbsent(participantId, PresenceInfo::new);
    }

    public void remove(String participantId) {
        presences.remove(participantId);
    }

    public Map<String, PresenceInfo> getAll() {
        return Collections.unmodifiableMap(presences);
    }
}
