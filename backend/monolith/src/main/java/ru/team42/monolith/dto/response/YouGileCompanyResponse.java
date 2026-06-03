package ru.team42.monolith.dto.response;

public record YouGileCompanyResponse(
        String id,
        String name,
        Boolean isAdmin
) {}
