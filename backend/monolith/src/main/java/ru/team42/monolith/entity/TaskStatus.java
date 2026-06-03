package ru.team42.monolith.entity;

public enum TaskStatus {
    OPEN,
    IN_PROGRESS,
    BLOCKED,
    REVIEW,
    DONE,
    CANCELLED;

    public boolean isTerminal() {
        return this == DONE || this == CANCELLED;
    }
}
