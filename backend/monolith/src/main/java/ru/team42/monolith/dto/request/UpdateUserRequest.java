package ru.team42.monolith.dto.request;

public record UpdateUserRequest(
        String firstName,
        String lastName
) {}
