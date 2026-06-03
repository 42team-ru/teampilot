package ru.team42.backend.kafka_common.event;

public final class KafkaTopics {

    private KafkaTopics() {}

    public static final String MESSAGES_RAW     = "messages.raw";
    public static final String MESSAGES_BATCHES = "messages.batches";
    public static final String LLM_TASKS_CREATE  = "llm.tasks.create";
    public static final String LLM_STATUS_CHANGE = "llm.status.change";
    public static final String AUDIO_NEW          = "audio.new";

    public static final String BOTS_TASKS           = "bots.tasks";
    public static final String BOTS_NOTIFICATIONS   = "bots.notifications";
    public static final String TASKS_STATUS_CHANGED = "tasks.status.changed";
}