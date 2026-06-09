package ru.team42.monolith.dto.payment;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.Map;

@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class YooKassaWebhookDto {

    private String event;

    @JsonProperty("object")
    private PaymentObject object;

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class PaymentObject {
        private String id;
        private String status;
        private Amount amount;
        @JsonProperty("paid")
        private boolean paid;
        @JsonProperty("metadata")
        private Map<String, String> metadata;
        private boolean test;
    }

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class Amount {
        private String value;
        private String currency;
    }
}
