package ru.team42.backend.kafka_common.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Data
@ConfigurationProperties(prefix = "app.kafka")
public class AppKafkaProperties {

    private int consumerConcurrency = 3;
    private String autoOffsetReset = "earliest";
    private String trustedPackages = "ru.team42.backend.*";
}