package ru.team42.monolith.config;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class PartialIndexInitializer {

    private final JdbcTemplate jdbcTemplate;

    @EventListener(ApplicationReadyEvent.class)
    public void createPartialIndexes() {
        jdbcTemplate.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_teams_telegram_chat_id_active " +
                "ON teams (telegram_chat_id) WHERE active = true"
        );
        log.info("Partial unique index uq_teams_telegram_chat_id_active ensured");
    }
}
