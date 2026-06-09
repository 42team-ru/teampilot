package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.client.YooKassaClient;
import ru.team42.monolith.config.YooKassaProperties;
import ru.team42.monolith.dto.payment.YooKassaWebhookDto;
import ru.team42.monolith.dto.request.AdminCreateTeamRequest;
import ru.team42.monolith.dto.response.TeamPaymentInitiateResponse;
import ru.team42.monolith.dto.response.TeamResponse;
import ru.team42.monolith.entity.TeamPayment;
import ru.team42.monolith.entity.enums.TeamPaymentStatus;
import ru.team42.monolith.repository.TeamPaymentRepository;

import java.math.BigDecimal;
import java.util.Map;

@Service
@RequiredArgsConstructor
@Slf4j
public class TeamPaymentService {

    private final YooKassaClient yooKassaClient;
    private final YooKassaProperties yooKassaProperties;
    private final TeamPaymentRepository teamPaymentRepository;
    private final TeamService teamService;
    private final NotificationEventPublisher notificationEventPublisher;

    @Value("${app.team-creation.price-rub:100.00}")
    private BigDecimal priceRub;

    @Value("${app.invite.bot-url:t.me/prorab_bot}")
    private String botUrl;

    @Transactional
    public TeamPaymentInitiateResponse initiate(Long telegramId, String teamName) {
        Map<String, String> metadata = Map.of(
                "telegramId", telegramId.toString(),
                "teamName", teamName
        );

        YooKassaClient.CreatePaymentResponse ykResponse = yooKassaClient.createPayment(
                priceRub,
                "RUB",
                "Создание команды «" + teamName + "»",
                yooKassaProperties.getReturnUrl(),
                metadata
        );

        if (ykResponse == null) {
            throw AppException.internalError("Ошибка при создании платежа в ЮKassa");
        }

        TeamPayment payment = new TeamPayment();
        payment.setYookassaPaymentId(ykResponse.getId());
        payment.setTelegramId(telegramId);
        payment.setTeamName(teamName);
        payment.setStatus(TeamPaymentStatus.PENDING);
        teamPaymentRepository.save(payment);

        String confirmationUrl = ykResponse.getConfirmation() != null
                ? ykResponse.getConfirmation().getConfirmationUrl()
                : null;

        String amount = ykResponse.getAmount() != null
                ? ykResponse.getAmount().getValue()
                : priceRub.toPlainString();

        log.info("Team payment initiated: paymentId={}, telegramId={}, teamName={}",
                ykResponse.getId(), telegramId, teamName);

        return new TeamPaymentInitiateResponse(confirmationUrl, amount, ykResponse.isTest());
    }

    @Transactional
    public void handleWebhook(YooKassaWebhookDto webhook) {
        String event = webhook.getEvent();
        YooKassaWebhookDto.PaymentObject payment = webhook.getObject();

        if (payment == null || payment.getMetadata() == null) {
            log.warn("Webhook without payment object or metadata: event={}", event);
            return;
        }

        String telegramIdStr = payment.getMetadata().get("telegramId");
        String teamName = payment.getMetadata().get("teamName");

        if (telegramIdStr == null || teamName == null) {
            log.debug("Webhook not for team creation (missing telegramId/teamName): event={}", event);
            return;
        }

        log.info("Team payment webhook: event={}, paymentId={}, telegramId={}, teamName={}",
                event, payment.getId(), telegramIdStr, teamName);

        switch (event) {
            case "payment.succeeded" -> handleSucceeded(payment, telegramIdStr, teamName);
            case "payment.canceled" -> handleCanceled(payment.getId());
            default -> log.debug("Unhandled webhook event for team payment: {}", event);
        }
    }

    private void handleSucceeded(YooKassaWebhookDto.PaymentObject payment,
                                  String telegramIdStr, String teamName) {
        if (!payment.isPaid()) {
            log.warn("payment.succeeded but paid=false, skipping: paymentId={}", payment.getId());
            return;
        }

        teamPaymentRepository.findByYookassaPaymentId(payment.getId()).ifPresent(p -> {
            if (p.getStatus() == TeamPaymentStatus.SUCCEEDED) {
                log.warn("Duplicate webhook for already succeeded payment: {}", payment.getId());
                return;
            }
            p.setStatus(TeamPaymentStatus.SUCCEEDED);
            teamPaymentRepository.save(p);
        });

        long telegramId;
        try {
            telegramId = Long.parseLong(telegramIdStr);
        } catch (NumberFormatException e) {
            log.error("Invalid telegramId in webhook metadata: {}", telegramIdStr);
            return;
        }

        AdminCreateTeamRequest req = new AdminCreateTeamRequest(
                null, teamName, null, null, telegramId, null
        );
        TeamResponse team = teamService.createWithAdmin(req);

        String inviteLink = "https://" + botUrl + "?start=join_" + team.id();

        notificationEventPublisher.publishTeamCreated(telegramId, team.id().toString(), teamName, inviteLink);

        log.info("Team created via payment: teamId={}, telegramId={}, teamName={}",
                team.id(), telegramId, teamName);
    }

    private void handleCanceled(String paymentId) {
        teamPaymentRepository.findByYookassaPaymentId(paymentId).ifPresent(p -> {
            p.setStatus(TeamPaymentStatus.FAILED);
            teamPaymentRepository.save(p);
            log.info("Team payment canceled: paymentId={}", paymentId);
        });
    }
}
