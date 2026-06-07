package ru.team42.backend.kafka_common.event;

public final class KafkaTopics {

    private KafkaTopics() {}

    public static final String MESSAGES_RAW     = "messages.raw";
    public static final String MESSAGES_BATCHES = "messages.batches";
    public static final String LLM_TASKS_CREATE  = "llm.tasks.create";
    public static final String LLM_TASKS_UPDATE  = "llm.tasks.update";
    public static final String LLM_STATUS_CHANGE = "llm.status.change";
    public static final String AUDIO_NEW          = "audio.new";
    public static final String FILES_UPLOADED     = "files.uploaded";
    public static final String BOTS_TASKS         = "bots.tasks";
    public static final String BOTS_NOTIFICATIONS  = "bots.notifications";
    public static final String TASKS_STATE             = "tasks.state";
    public static final String TASKS_LIFECYCLE         = "tasks.lifecycle";
    public static final String FILES_TRANSCRIPT_READY  = "files.transcript_ready";
    public static final String SYNC_REQUESTS           = "sync.requests";
    public static final String SYNC_DRAFT              = "sync.draft";
    public static final String MEETINGS_AUDIO_CHUNKS   = "meetings.audio.chunks";
    public static final String MEETINGS_LIVE_RESULTS   = "meetings.live.results";
}
