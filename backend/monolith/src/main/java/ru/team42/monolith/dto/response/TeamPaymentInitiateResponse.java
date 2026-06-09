package ru.team42.monolith.dto.response;

public record TeamPaymentInitiateResponse(
        String confirmationUrl,
        String amount,
        boolean test
) {}
