package ru.team42.monolith.client;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import ru.team42.monolith.config.YooKassaProperties;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Component
@RequiredArgsConstructor
@Slf4j
public class YooKassaClient {

    private final YooKassaProperties props;

    public CreatePaymentResponse createPayment(BigDecimal amount, String currency,
                                                String description, String returnUrl,
                                                Map<String, String> metadata) {
        String idempotenceKey = UUID.randomUUID().toString();

        CreatePaymentRequest body = new CreatePaymentRequest();
        body.setAmount(new AmountDto(amount.toPlainString(), currency));
        body.setConfirmation(new ConfirmationDto("redirect", returnUrl));
        body.setCapture(true);
        body.setDescription(description);
        body.setMetadata(metadata);

        RestClient restClient = buildClient();

        CreatePaymentResponse response = restClient.post()
                .uri("/payments")
                .header("Idempotence-Key", idempotenceKey)
                .contentType(MediaType.APPLICATION_JSON)
                .body(body)
                .retrieve()
                .body(CreatePaymentResponse.class);

        log.info("Created YooKassa payment: id={}, status={}",
                response != null ? response.getId() : null,
                response != null ? response.getStatus() : null);

        return response;
    }

    private RestClient buildClient() {
        return RestClient.builder()
                .baseUrl(props.getApiUrl())
                .defaultHeaders(headers -> {
                    headers.setBasicAuth(props.getShopId(), props.getSecretKey());
                    headers.setContentType(MediaType.APPLICATION_JSON);
                    headers.setAccept(List.of(MediaType.APPLICATION_JSON));
                })
                .build();
    }

    @Data
    public static class CreatePaymentRequest {
        private AmountDto amount;
        private ConfirmationDto confirmation;
        private boolean capture = true;
        private String description;
        private Map<String, String> metadata;
    }

    @Data
    public static class AmountDto {
        private final String value;
        private final String currency;
    }

    @Data
    public static class ConfirmationDto {
        private final String type;
        @JsonProperty("return_url")
        private final String returnUrl;
    }

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class CreatePaymentResponse {
        private String id;
        private String status;
        private boolean paid;
        private AmountDto amount;
        private ConfirmationResponseDto confirmation;
        @JsonProperty("created_at")
        private String createdAt;
        private String description;
        private Map<String, String> metadata;
        private boolean test;
    }

    @Data
    @JsonIgnoreProperties(ignoreUnknown = true)
    public static class ConfirmationResponseDto {
        private String type;
        @JsonProperty("return_url")
        private String returnUrl;
        @JsonProperty("confirmation_url")
        private String confirmationUrl;
    }
}
