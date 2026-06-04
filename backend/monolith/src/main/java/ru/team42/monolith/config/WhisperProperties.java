package ru.team42.monolith.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "app.whisper")
public class WhisperProperties {
    private String baseUrl = "http://localhost:8002";
    private String endpoint = "/inference";
    private String model = "whisper-1";
    private String language = "ru";
    private int timeoutSeconds = 120;
}
