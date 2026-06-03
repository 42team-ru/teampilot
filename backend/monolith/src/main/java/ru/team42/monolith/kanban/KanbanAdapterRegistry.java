package ru.team42.monolith.kanban;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import ru.team42.monolith.entity.KanbanProvider;

import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

@Slf4j
@Component
public class KanbanAdapterRegistry {

    private final Map<KanbanProvider, KanbanBoardAdapter> adapters;

    public KanbanAdapterRegistry(List<KanbanBoardAdapter> adapterList) {
        this.adapters = adapterList.stream()
                .collect(Collectors.toMap(KanbanBoardAdapter::supports, Function.identity()));
        log.info("Registered kanban adapters: {}", adapters.keySet());
    }

    public KanbanBoardAdapter get(KanbanProvider provider) {
        KanbanBoardAdapter adapter = adapters.get(provider);
        if (adapter == null) {
            throw new IllegalArgumentException("No adapter registered for provider: " + provider);
        }
        return adapter;
    }

    public boolean supports(KanbanProvider provider) {
        return adapters.containsKey(provider);
    }
}
