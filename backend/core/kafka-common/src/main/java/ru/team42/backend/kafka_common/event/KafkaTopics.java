package ru.team42.backend.kafka_common.event;

public final class KafkaTopics {

    private KafkaTopics() {}

    public static final String MESSAGES_RAW     = "messages.raw";
    public static final String MESSAGES_BATCHES = "messages.batches";
    public static final String LLM_TASKS_CREATE  = "llm.tasks.create";
    public static final String LLM_STATUS_CHANGE = "llm.status.change";
}