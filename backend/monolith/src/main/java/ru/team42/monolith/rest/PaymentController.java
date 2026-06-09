package ru.team42.monolith.rest;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.dto.payment.YooKassaWebhookDto;
import ru.team42.monolith.dto.request.InitiateTeamPaymentRequest;
import ru.team42.monolith.dto.response.TeamPaymentInitiateResponse;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.service.TeamPaymentService;

@RestController
@RequestMapping("/payments")
@RequiredArgsConstructor
@Tag(name = "Payment", description = "Оплата создания команды через ЮKassa")
public class PaymentController {

    private final TeamPaymentService teamPaymentService;

    @Operation(summary = "Инициировать оплату создания команды")
    @PostMapping("/team")
    public ResponseEntity<TeamPaymentInitiateResponse> initiateTeamPayment(
            @AuthenticationPrincipal User currentUser,
            @Valid @RequestBody InitiateTeamPaymentRequest request
    ) {
        if (currentUser == null) {
            throw AppException.unauthorized("Telegram user authentication required");
        }
        return ResponseUtils.created(
                "/payments/team",
                teamPaymentService.initiate(currentUser.getTelegramId(), request.teamName())
        );
    }

    @Operation(summary = "Webhook от ЮKassa (публичный)")
    @PostMapping("/webhook")
    public ResponseEntity<Void> webhook(@RequestBody YooKassaWebhookDto webhook) {
        teamPaymentService.handleWebhook(webhook);
        return ResponseEntity.ok().build();
    }
}
