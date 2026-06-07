package ru.team42.monolith.service;

import org.springframework.stereotype.Service;
import ru.team42.monolith.event.SyncDraftEvent;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Service
public class SyncStateService {

    public enum UserSyncStatus { AWAITING, DRAFT_SENT, CONFIRMED, REJECTED }

    public record UserSyncState(
            Long telegramId,
            String username,
            UserSyncStatus status,
            String rawText,
            String requestId,
            List<SyncDraftEvent.DraftItem> draft,
            int confirmedTasksCount,
            int pendingTasksCount
    ) {
        public UserSyncState withStatus(UserSyncStatus newStatus) {
            return new UserSyncState(telegramId, username, newStatus, rawText, requestId, draft, confirmedTasksCount, pendingTasksCount);
        }

        public UserSyncState withResponse(String text, String reqId) {
            return new UserSyncState(telegramId, username, UserSyncStatus.AWAITING, text, reqId, draft, confirmedTasksCount, pendingTasksCount);
        }

        public UserSyncState withDraft(List<SyncDraftEvent.DraftItem> items) {
            return new UserSyncState(telegramId, username, UserSyncStatus.DRAFT_SENT, rawText, requestId, items, confirmedTasksCount, pendingTasksCount);
        }

        public UserSyncState addConfirmCounts(int addConfirmed, int addPending) {
            return new UserSyncState(telegramId, username, UserSyncStatus.CONFIRMED, rawText, requestId, draft,
                    confirmedTasksCount + addConfirmed, pendingTasksCount + addPending);
        }
    }

    public record TeamSyncSession(
            UUID teamId,
            Long chatId,
            Instant startedAt,
            Map<Long, UserSyncState> userStates
    ) {}

    private final Map<UUID, TeamSyncSession> sessions = new ConcurrentHashMap<>();
    private final Map<Long, UUID> chatIdToTeamId = new ConcurrentHashMap<>();
    private final Map<String, Long> requestIdToUser = new ConcurrentHashMap<>();

    public void openSession(UUID teamId, Long chatId, List<Long> memberTelegramIds, List<String> usernames) {
        Map<Long, UserSyncState> states = new ConcurrentHashMap<>();
        for (int i = 0; i < memberTelegramIds.size(); i++) {
            Long id = memberTelegramIds.get(i);
            String name = i < usernames.size() ? usernames.get(i) : id.toString();
            states.put(id, new UserSyncState(id, name, UserSyncStatus.AWAITING, null, null, List.of(), 0, 0));
        }
        sessions.put(teamId, new TeamSyncSession(teamId, chatId, Instant.now(), states));
        chatIdToTeamId.put(chatId, teamId);
    }

    public void closeSession(UUID teamId) {
        TeamSyncSession session = sessions.remove(teamId);
        if (session != null) {
            chatIdToTeamId.remove(session.chatId());
            session.userStates().values().forEach(u -> {
                if (u.requestId() != null) requestIdToUser.remove(u.requestId());
            });
        }
    }

    public boolean isInSyncWindow(Long chatId) {
        return chatIdToTeamId.containsKey(chatId);
    }

    public Optional<UUID> getTeamIdByChatId(Long chatId) {
        return Optional.ofNullable(chatIdToTeamId.get(chatId));
    }

    public Optional<TeamSyncSession> getSession(UUID teamId) {
        return Optional.ofNullable(sessions.get(teamId));
    }

    public void recordUserResponse(UUID teamId, Long telegramId, String text, String requestId) {
        sessions.computeIfPresent(teamId, (id, session) -> {
            Map<Long, UserSyncState> updated = new ConcurrentHashMap<>(session.userStates());
            updated.computeIfPresent(telegramId, (uid, state) -> state.withResponse(text, requestId));
            requestIdToUser.put(requestId, telegramId);
            return new TeamSyncSession(session.teamId(), session.chatId(), session.startedAt(), updated);
        });
    }

    public void storeDraft(UUID teamId, String requestId, List<SyncDraftEvent.DraftItem> items) {
        Long telegramId = requestIdToUser.get(requestId);
        if (telegramId == null) return;
        sessions.computeIfPresent(teamId, (id, session) -> {
            Map<Long, UserSyncState> updated = new ConcurrentHashMap<>(session.userStates());
            updated.computeIfPresent(telegramId, (uid, state) -> state.withDraft(items));
            return new TeamSyncSession(session.teamId(), session.chatId(), session.startedAt(), updated);
        });
    }

    public Optional<UserSyncState> getUserState(UUID teamId, Long telegramId) {
        return getSession(teamId).map(s -> s.userStates().get(telegramId));
    }

    public void addConfirmCounts(UUID teamId, Long telegramId, int confirmed, int pending) {
        sessions.computeIfPresent(teamId, (id, session) -> {
            Map<Long, UserSyncState> updated = new ConcurrentHashMap<>(session.userStates());
            updated.computeIfPresent(telegramId, (uid, state) -> state.addConfirmCounts(confirmed, pending));
            return new TeamSyncSession(session.teamId(), session.chatId(), session.startedAt(), updated);
        });
    }

    public void updateUserStatus(UUID teamId, Long telegramId, UserSyncStatus status) {
        sessions.computeIfPresent(teamId, (id, session) -> {
            Map<Long, UserSyncState> updated = new ConcurrentHashMap<>(session.userStates());
            updated.computeIfPresent(telegramId, (uid, state) -> state.withStatus(status));
            return new TeamSyncSession(session.teamId(), session.chatId(), session.startedAt(), updated);
        });
    }

    public Optional<Long> getUserByRequestId(String requestId) {
        return Optional.ofNullable(requestIdToUser.get(requestId));
    }

    public Optional<UUID> getTeamIdByUserId(Long telegramUserId) {
        return sessions.values().stream()
                .filter(s -> s.userStates().containsKey(telegramUserId))
                .map(TeamSyncSession::teamId)
                .findFirst();
    }

    public Collection<TeamSyncSession> getAllSessions() {
        return sessions.values();
    }
}
