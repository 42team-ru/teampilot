package ru.team42.monolith.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "app")
public class AppProperties {

    private Bot bot = new Bot();
    private Jwt jwt = new Jwt();
    private Telegram telegram = new Telegram();
    private Llm llm = new Llm();

    @Data
    public static class Bot {
        private String secret = "changeme";
    }

    @Data
    public static class Jwt {
        private String secret;
        private int expirationDays;
    }

    @Data
    public static class Telegram {
        private String botToken;
    }

    @Data
    public static class Llm {
        private float autoConfirmThreshold = 0.90f;
    }
}
