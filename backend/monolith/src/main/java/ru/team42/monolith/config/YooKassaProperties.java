package ru.team42.monolith.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties("app.yookassa")
public class YooKassaProperties {

    private String apiUrl = "https://api.yookassa.ru/v3";
    private String shopId;
    private String secretKey;
    private String returnUrl;
}
