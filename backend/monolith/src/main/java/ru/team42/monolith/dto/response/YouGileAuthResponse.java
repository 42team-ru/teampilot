package ru.team42.monolith.dto.response;

import java.util.List;

public record YouGileAuthResponse(
        boolean connected,                   // true — API key saved, ready for board selection
        List<YouGileCompanyResponse> companies,  // non-null when multiple companies found
        List<YouGileBoardResponse> boards        // non-null when connected
) {}
