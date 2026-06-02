package ru.team42.backend.kafka_common.event;

public final class KafkaTopics {

    private KafkaTopics() {}

    public static final String USER_CREATED = "user-created-events";
    public static final String USER_UPDATED = "user-updated-events";
}