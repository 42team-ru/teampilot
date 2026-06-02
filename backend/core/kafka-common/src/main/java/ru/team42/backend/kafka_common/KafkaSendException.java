package ru.team42.backend.kafka_common;

/**
 * Выбрасывается {@link KafkaSender}, когда отправка сообщения завершилась с ошибкой,
 * таймаутом или была прервана.
 */
public class KafkaSendException extends RuntimeException {

    public KafkaSendException(String message, Throwable cause) {
        super(message, cause);
    }
}
