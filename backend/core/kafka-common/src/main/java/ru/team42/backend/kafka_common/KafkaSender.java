package ru.team42.backend.kafka_common;

import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import ru.team42.backend.kafka_common.event.BaseEvent;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

@Slf4j
public class KafkaSender {

    private static final long DEFAULT_SYNC_TIMEOUT_SECONDS = 10;

    private final KafkaTemplate<String, BaseEvent> kafkaTemplate;

    public KafkaSender(KafkaTemplate<String, BaseEvent> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    public void send(String topic, String key, BaseEvent payload) {
        sendAsync(topic, key, payload).whenComplete((result, ex) -> {
            if (ex != null) {
                log.error("Failed to send to topic={} key={} type={}: {}",
                        topic, key, payload.getClass().getSimpleName(), ex.getMessage(), ex);
            } else {
                log.debug("Sent to topic={} key={} type={} partition={} offset={}",
                        topic, key,
                        payload.getClass().getSimpleName(),
                        result.getRecordMetadata().partition(),
                        result.getRecordMetadata().offset());
            }
        });
    }

    public CompletableFuture<SendResult<String, BaseEvent>> sendAsync(
            String topic, String key, BaseEvent payload) {
        log.trace("Sending to topic={} key={} type={}", topic, key, payload.getClass().getSimpleName());
        return kafkaTemplate.send(topic, key, payload);
    }

    public SendResult<String, BaseEvent> sendSync(String topic, String key, BaseEvent payload) {
        return sendSync(topic, key, payload, DEFAULT_SYNC_TIMEOUT_SECONDS, TimeUnit.SECONDS);
    }

    public SendResult<String, BaseEvent> sendSync(
            String topic, String key, BaseEvent payload, long timeout, TimeUnit unit) {
        try {
            SendResult<String, BaseEvent> result =
                    sendAsync(topic, key, payload).get(timeout, unit);
            log.debug("Sync send confirmed: topic={} key={} type={} offset={}",
                    topic, key,
                    payload.getClass().getSimpleName(),
                    result.getRecordMetadata().offset());
            return result;
        } catch (TimeoutException e) {
            throw new KafkaSendException(
                    "Timed out waiting for send confirmation: topic=%s key=%s".formatted(topic, key), e);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new KafkaSendException(
                    "Interrupted while waiting for send confirmation: topic=%s key=%s".formatted(topic, key), e);
        } catch (ExecutionException e) {
            throw new KafkaSendException(
                    "Send failed: topic=%s key=%s cause=%s".formatted(topic, key, e.getCause().getMessage()),
                    e.getCause());
        }
    }
}
