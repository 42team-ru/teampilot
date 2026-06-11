package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.monolith.entity.SyncSession;
import ru.team42.monolith.entity.SyncUserState;
import ru.team42.monolith.entity.enums.UserSyncStatus;
import ru.team42.monolith.event.SyncDraftEvent;
import ru.team42.monolith.repository.SyncSessionRepository;
import ru.team42.monolith.repository.SyncUserStateRepository;

import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class SyncStateService {


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

    private final SyncSessionRepository syncSessionRepository;
    private final SyncUserStateRepository syncUserStateRepository;

    @Transactional
    public void openSession(UUID teamId, Long chatId, List<Long> memberTelegramIds, List<String> usernames) {
        // Delete existing session if any (with cascade)
        syncSessionRepository.deleteById(teamId);
        syncSessionRepository.flush();

        SyncSession session = new SyncSession();
        session.setTeamId(teamId);
        session.setChatId(chatId);
        session.setStartedAt(Instant.now());
        session = syncSessionRepository.save(session);

        for (int i = 0; i < memberTelegramIds.size(); i++) {
            Long id = memberTelegramIds.get(i);
            String name = i < usernames.size() ? usernames.get(i) : id.toString();

            SyncUserState userState = new SyncUserState();
            userState.setSession(session);
            userState.setTelegramId(id);
            userState.setUsername(name);
            userState.setStatus(UserSyncStatus.AWAITING);
            userState.setDraft(List.of());
            userState.setConfirmedTasksCount(0);
            userState.setPendingTasksCount(0);
            syncUserStateRepository.save(userState);
        }
    }

    @Transactional
    public void closeSession(UUID teamId) {
        syncSessionRepository.deleteById(teamId);
    }

    @Transactional(readOnly = true)
    public boolean isInSyncWindow(Long chatId) {
        return syncSessionRepository.existsByChatId(chatId);
    }

    @Transactional(readOnly = true)
    public Optional<UUID> getTeamIdByChatId(Long chatId) {
        return syncSessionRepository.findByChatId(chatId).map(SyncSession::getTeamId);
    }

    @Transactional(readOnly = true)
    public Optional<TeamSyncSession> getSession(UUID teamId) {
        return syncSessionRepository.findById(teamId).map(this::toTeamSyncSession);
    }

    @Transactional
    public void recordUserResponse(UUID teamId, Long telegramId, String text, String requestId) {
        syncUserStateRepository.findBySessionTeamIdAndTelegramId(teamId, telegramId).ifPresent(userState -> {
            userState.setRawText(text);
            userState.setRequestId(requestId);
            syncUserStateRepository.save(userState);
        });
    }

    @Transactional
    public void storeDraft(UUID teamId, String requestId, List<SyncDraftEvent.DraftItem> items) {
        syncUserStateRepository.findByRequestId(requestId).ifPresent(userState -> {
            userState.setDraft(items);
            userState.setStatus(UserSyncStatus.DRAFT_SENT);
            syncUserStateRepository.save(userState);
        });
    }

    @Transactional(readOnly = true)
    public Optional<UserSyncState> getUserState(UUID teamId, Long telegramId) {
        return syncUserStateRepository.findBySessionTeamIdAndTelegramId(teamId, telegramId)
                .map(this::toUserSyncState);
    }

    @Transactional
    public void addConfirmCounts(UUID teamId, Long telegramId, int confirmed, int pending) {
        syncUserStateRepository.findBySessionTeamIdAndTelegramId(teamId, telegramId).ifPresent(userState -> {
            userState.setConfirmedTasksCount(userState.getConfirmedTasksCount() + confirmed);
            userState.setPendingTasksCount(userState.getPendingTasksCount() + pending);
            userState.setStatus(UserSyncStatus.CONFIRMED);
            syncUserStateRepository.save(userState);
        });
    }

    @Transactional
    public void updateUserStatus(UUID teamId, Long telegramId, UserSyncStatus status) {
        syncUserStateRepository.findBySessionTeamIdAndTelegramId(teamId, telegramId).ifPresent(userState -> {
            userState.setStatus(status);
            syncUserStateRepository.save(userState);
        });
    }

    @Transactional(readOnly = true)
    public Optional<Long> getUserByRequestId(String requestId) {
        return syncUserStateRepository.findByRequestId(requestId).map(SyncUserState::getTelegramId);
    }

    @Transactional(readOnly = true)
    public Optional<UUID> getTeamIdByUserId(Long telegramUserId) {
        return syncUserStateRepository.findFirstByTelegramId(telegramUserId)
                .map(u -> u.getSession().getTeamId());
    }

    @Transactional(readOnly = true)
    public Collection<TeamSyncSession> getAllSessions() {
        return syncSessionRepository.findAll().stream()
                .map(this::toTeamSyncSession)
                .toList();
    }

    private TeamSyncSession toTeamSyncSession(SyncSession session) {
        List<SyncUserState> userStates = syncUserStateRepository.findBySessionTeamId(session.getTeamId());
        Map<Long, UserSyncState> stateMap = userStates.stream()
                .collect(Collectors.toMap(SyncUserState::getTelegramId, this::toUserSyncState));
        return new TeamSyncSession(session.getTeamId(), session.getChatId(), session.getStartedAt(), stateMap);
    }

    private UserSyncState toUserSyncState(SyncUserState entity) {
        return new UserSyncState(
                entity.getTelegramId(),
                entity.getUsername(),
                entity.getStatus(),
                entity.getRawText(),
                entity.getRequestId(),
                entity.getDraft() != null ? entity.getDraft() : List.of(),
                entity.getConfirmedTasksCount(),
                entity.getPendingTasksCount()
        );
    }
}
