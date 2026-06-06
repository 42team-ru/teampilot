package ru.team42.backend.kafka_common.config;

import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.kafka.autoconfigure.KafkaProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.config.TopicBuilder;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.core.DefaultKafkaConsumerFactory;
import org.springframework.kafka.core.DefaultKafkaProducerFactory;
import org.springframework.kafka.core.KafkaAdmin;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.core.ProducerFactory;
import org.springframework.kafka.listener.ContainerProperties;
import org.springframework.kafka.support.serializer.ErrorHandlingDeserializer;
import ru.team42.backend.kafka_common.KafkaSender;
import ru.team42.backend.kafka_common.event.BaseEvent;
import ru.team42.backend.kafka_common.event.KafkaTopics;

import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.ArrayList;
import java.util.List;

@AutoConfiguration(beforeName = "org.springframework.boot.kafka.autoconfigure.KafkaAutoConfiguration")
@ConditionalOnClass(KafkaTemplate.class)
@EnableConfigurationProperties({KafkaProperties.class, AppKafkaProperties.class})
public class KafkaAutoConfiguration {

    private static final String JACKSON_JSON_SERIALIZER =
        "org.springframework.kafka.support.serializer.JacksonJsonSerializer";

    @Bean
    public ProducerFactory<String, BaseEvent> kafkaProducerFactory(KafkaProperties kafkaProps) {
        var props = kafkaProps.buildProducerProperties();
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, JACKSON_JSON_SERIALIZER);
        props.put(ProducerConfig.ACKS_CONFIG, "all");
        props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
        props.put(ProducerConfig.RETRIES_CONFIG, 3);
        return new DefaultKafkaProducerFactory<>(props);
    }

    @Bean
    public KafkaTemplate<String, BaseEvent> kafkaTemplate(
            ProducerFactory<String, BaseEvent> kafkaProducerFactory) {
        return new KafkaTemplate<>(kafkaProducerFactory);
    }

    @Bean
    @ConditionalOnMissingBean
    public KafkaSender kafkaSender(KafkaTemplate<String, BaseEvent> kafkaTemplate) {
        return new KafkaSender(kafkaTemplate);
    }

    @Bean
    @ConditionalOnMissingBean(ConsumerFactory.class)
    public ConsumerFactory<String, Object> kafkaConsumerFactory(
            KafkaProperties kafkaProps,
            AppKafkaProperties appProps) {
        var props = kafkaProps.buildConsumerProperties();
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, ErrorHandlingDeserializer.class);
        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, ErrorHandlingDeserializer.class);
        props.put(ErrorHandlingDeserializer.KEY_DESERIALIZER_CLASS, StringDeserializer.class.getName());
        props.put(ErrorHandlingDeserializer.VALUE_DESERIALIZER_CLASS, StringDeserializer.class.getName());
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, false);
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, appProps.getAutoOffsetReset());
        return new DefaultKafkaConsumerFactory<>(props);
    }

    @Bean
    @ConditionalOnMissingBean(name = "kafkaListenerContainerFactory")
    public ConcurrentKafkaListenerContainerFactory<String, Object> kafkaListenerContainerFactory(
            ConsumerFactory<String, Object> kafkaConsumerFactory,
            AppKafkaProperties appProps) {
        var factory = new ConcurrentKafkaListenerContainerFactory<String, Object>();
        factory.setConsumerFactory(kafkaConsumerFactory);
        factory.getContainerProperties().setAckMode(ContainerProperties.AckMode.BATCH);
        factory.setConcurrency(appProps.getConsumerConcurrency());
        return factory;
    }

    @Bean
    public KafkaAdmin.NewTopics kafkaTopics(AppKafkaProperties appProps) {
        List<org.apache.kafka.clients.admin.NewTopic> topics = new ArrayList<>();
        for (Field field : KafkaTopics.class.getDeclaredFields()) {
            if (Modifier.isPublic(field.getModifiers())
                    && Modifier.isStatic(field.getModifiers())
                    && Modifier.isFinal(field.getModifiers())
                    && field.getType() == String.class) {
                try {
                    String topicName = (String) field.get(null);
                    topics.add(TopicBuilder.name(topicName)
                            .partitions(appProps.getDefaultPartitions())
                            .replicas(appProps.getDefaultReplicationFactor())
                            .build());
                } catch (IllegalAccessException ignored) {}
            }
        }
        return new KafkaAdmin.NewTopics(topics.toArray(new org.apache.kafka.clients.admin.NewTopic[0]));
    }
}