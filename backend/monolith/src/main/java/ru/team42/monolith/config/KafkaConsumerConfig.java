package ru.team42.monolith.config;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationContext;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.PropertyNamingStrategies;
import com.fasterxml.jackson.databind.deser.std.StdDeserializer;
import com.fasterxml.jackson.databind.json.JsonMapper;
import com.fasterxml.jackson.databind.module.SimpleModule;

import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.jspecify.annotations.Nullable;

import org.springframework.boot.kafka.autoconfigure.ConcurrentKafkaListenerContainerFactoryConfigurer;
import org.springframework.boot.kafka.autoconfigure.KafkaProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.DefaultKafkaConsumerFactory;
import org.springframework.kafka.support.KafkaNull;
import org.springframework.kafka.support.converter.ConversionException;
import org.springframework.kafka.support.converter.MessagingMessageConverter;

import java.io.IOException;
import java.lang.reflect.Type;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeParseException;

@Configuration
public class KafkaConsumerConfig {

    @Bean
    public ConcurrentKafkaListenerContainerFactory<?, ?> kafkaListenerContainerFactory(
            ConcurrentKafkaListenerContainerFactoryConfigurer configurer,
            KafkaProperties kafkaProperties) {

        var consumerFactory = new DefaultKafkaConsumerFactory<>(kafkaProperties.buildConsumerProperties());
        var factory = new ConcurrentKafkaListenerContainerFactory<>();
        configurer.configure(factory, consumerFactory);
        factory.setRecordMessageConverter(new Jackson2RecordMessageConverter());
        return factory;
    }

    /**
     * Uses Jackson 2.x so that @Jacksonized / @Builder event classes deserialize correctly.
     * Jackson 3.x (used by JacksonJsonMessageConverter) ignores com.fasterxml @JsonDeserialize.
     */
    static class Jackson2RecordMessageConverter extends MessagingMessageConverter {

        private final ObjectMapper mapper = JsonMapper.builder()
                .addModule(lenientInstantModule())
                .propertyNamingStrategy(PropertyNamingStrategies.SNAKE_CASE)
                .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
                .build();

        @Override
        protected Object extractAndConvertValue(ConsumerRecord<?, ?> record, @Nullable Type type) {
            if (record.value() == null) {
                return KafkaNull.INSTANCE;
            }
            String json = record.value().toString();
            try {
                return mapper.readValue(json, type != null
                        ? mapper.constructType(type)
                        : mapper.constructType(Object.class));
            } catch (JsonProcessingException e) {
                throw new ConversionException("Failed to convert from JSON for topic " + record.topic(), record, e);
            }
        }

        // Python worker sends "2026-06-05T23:59:00" without Z — treat as UTC
        private static SimpleModule lenientInstantModule() {
            var module = new SimpleModule();
            module.addDeserializer(Instant.class, new StdDeserializer<>(Instant.class) {
                @Override
                public Instant deserialize(JsonParser p, DeserializationContext ctxt) throws IOException {
                    String text = p.getText().trim();
                    try {
                        return Instant.parse(text);
                    } catch (DateTimeParseException ignored) {
                        return LocalDateTime.parse(text).toInstant(ZoneOffset.UTC);
                    }
                }
            });
            return module;
        }
    }
}
