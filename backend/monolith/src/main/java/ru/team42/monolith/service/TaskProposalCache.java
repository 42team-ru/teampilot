package ru.team42.monolith.service;

import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class TaskProposalCache {

    private final Map<String, PendingProposal> store = new ConcurrentHashMap<>();

    public record PendingProposal(String title, Long reporterTelegramId, UUID teamId) {}

    public String put(PendingProposal proposal) {
        String id = UUID.randomUUID().toString().replace("-", "");
        store.put(id, proposal);
        return id;
    }

    public Optional<PendingProposal> get(String id) {
        return Optional.ofNullable(store.get(id));
    }

    public void remove(String id) {
        store.remove(id);
    }
}
