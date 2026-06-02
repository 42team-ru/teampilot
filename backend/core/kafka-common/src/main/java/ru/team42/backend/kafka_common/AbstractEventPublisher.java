package ru.team42.backend.kafka_common;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.support.SendResult;
import ru.team42.backend.kafka_common.event.BaseEvent;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;

public abstract class AbstractEventPublisher {

    @Autowired
    private KafkaSender kafkaSender;

    protected void send(String topic, String key, BaseEvent event) {
        kafkaSender.send(topic, key, event);
    }

    protected CompletableFuture<SendResult<String, BaseEvent>> sendAsync(
            String topic, String key, BaseEvent event) {
        return kafkaSender.sendAsync(topic, key, event);
    }

    protected SendResult<String, BaseEvent> sendSync(String topic, String key, BaseEvent event) {
        return kafkaSender.sendSync(topic, key, event);
    }

    protected SendResult<String, BaseEvent> sendSync(
            String topic, String key, BaseEvent event, long timeout, TimeUnit unit) {
        return kafkaSender.sendSync(topic, key, event, timeout, unit);
    }
}