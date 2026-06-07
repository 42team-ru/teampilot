package ru.team42.monolith.scheduler;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import ru.team42.monolith.service.EveningSyncService;

@Slf4j
@Component
@RequiredArgsConstructor
public class EveningSyncScheduler {

    private final EveningSyncService eveningSyncService;

    @Scheduled(cron = "0 0 18 * * *")
    public void triggerEveningSync() {
        log.info("Evening sync trigger started");
        eveningSyncService.startSyncForAllTeams();
    }

    @Scheduled(cron = "0 0 19 * * *")
    public void closeSyncWindow() {
        log.info("Evening sync window closing — sending summaries");
        eveningSyncService.closeSyncAndSendSummary();
    }
}
