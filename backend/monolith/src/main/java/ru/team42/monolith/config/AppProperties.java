package ru.team42.monolith.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "app")
public class AppProperties {

    private Bot bot = new Bot();

    @Data
    public static class Bot {
        private String secret = "changeme";
    }
}
