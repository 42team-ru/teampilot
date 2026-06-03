package ru.team42.monolith.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "app")
public class AppProperties {

    private Bot bot = new Bot();
    private Invite invite = new Invite();

    @Data
    public static class Bot {
        private String secret = "changeme";
    }

    @Data
    public static class Invite {
        private long expirationDays = 7;
        private String botUrl = "t.me/digital_42TEAMbot";
    }
}
