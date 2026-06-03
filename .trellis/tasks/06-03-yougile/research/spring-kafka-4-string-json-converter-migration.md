# Research: Spring Kafka 4.0 StringJsonMessageConverter Replacement

- **Query**: What replaces `StringJsonMessageConverter` in Spring Kafka 4.0+?
- **Scope**: External (Spring Kafka source + official docs)
- **Date**: 2026-06-03

## Findings

### Deprecation Declaration

`StringJsonMessageConverter` is marked `@Deprecated(forRemoval = true, since = "4.0")`.

The Javadoc says verbatim:

> @deprecated since 4.0 in favor of {@link StringJacksonJsonMessageConverter} for Jackson 3.

Source:
`org.springframework.kafka.support.converter.StringJsonMessageConverter` (spring-kafka 4.0.x)

---

### Replacement Class

**`org.springframework.kafka.support.converter.StringJacksonJsonMessageConverter`**

- Introduced in Spring Kafka 4.0 (`@since 4.0`)
- Extends `JacksonJsonMessageConverter` (which replaces the old `JsonMessageConverter` family)
- Uses `tools.jackson.databind.json.JsonMapper` (Jackson 3) instead of `com.fasterxml.jackson.databind.ObjectMapper` (Jackson 2)
- Same contract as `StringJsonMessageConverter`: String on output, String/Bytes/byte[] on input
- Works with Kafka `StringSerializer` / `StringDeserializer` pair (same as before)

Constructor signatures:
```java
public StringJacksonJsonMessageConverter()
public StringJacksonJsonMessageConverter(JsonMapper objectMapper)
```

---

### Type Inference Without Headers

`JacksonJsonMessageConverter.determineJavaType()` logic:

1. Default `TypePrecedence` on `DefaultJacksonJavaTypeMapper` is `INFERRED`
2. When `TypePrecedence.INFERRED` and the listener method provides a `type` (from method parameter), it uses that type directly — **no `__TypeId__` header required**
3. If no headers and no inferred type, falls back to `Object`

This means **`@KafkaListener` methods typed to a specific DTO class will still work without type headers**, exactly like `StringJsonMessageConverter` did.

---

### Migration Pattern

**Before (Spring Kafka < 4.0 / deprecated):**
```java
factory.setRecordMessageConverter(new StringJsonMessageConverter());
```

**After (Spring Kafka 4.0+):**
```java
factory.setRecordMessageConverter(new StringJacksonJsonMessageConverter());
```

Full bean example:
```java
import org.springframework.kafka.support.converter.StringJacksonJsonMessageConverter;

@Bean
@ConditionalOnMissingBean(name = "kafkaListenerContainerFactory")
public ConcurrentKafkaListenerContainerFactory<String, Object> kafkaListenerContainerFactory(
        ConsumerFactory<String, Object> kafkaConsumerFactory,
        AppKafkaProperties appProps) {
    var factory = new ConcurrentKafkaListenerContainerFactory<String, Object>();
    factory.setConsumerFactory(kafkaConsumerFactory);
    factory.setRecordMessageConverter(new StringJacksonJsonMessageConverter());
    factory.getContainerProperties().setAckMode(ContainerProperties.AckMode.BATCH);
    factory.setConcurrency(appProps.getConsumerConcurrency());
    return factory;
}
```

No other changes needed — the API is a drop-in replacement.

---

### Jackson 3 Context (from What's New in 4.0 docs)

The official Spring Kafka 4.0 docs state:

> `JacksonJsonMessageConverter` family replaces `JsonMessageConverter` family.
> All Jackson 2 classes are deprecated but remain fully functional.
> To migrate to Jackson 3, simply add Jackson 3 to your classpath and update class references.

Spring Boot 4.0 ships with Jackson 3 by default (Jackson 2 is no longer the default), so `StringJacksonJsonMessageConverter` is the correct class to use.

---

### File to Change in This Project

| File | Line | Change |
|---|---|---|
| `backend/core/kafka-common/src/main/java/ru/team42/backend/kafka_common/config/KafkaAutoConfiguration.java` | 19, 78 | Replace import + usage |

Old import (line 19):
```java
import org.springframework.kafka.support.converter.StringJsonMessageConverter;
```

New import:
```java
import org.springframework.kafka.support.converter.StringJacksonJsonMessageConverter;
```

Old usage (line 78):
```java
factory.setRecordMessageConverter(new StringJsonMessageConverter());
```

New usage:
```java
factory.setRecordMessageConverter(new StringJacksonJsonMessageConverter());
```

---

## External References

- [Spring Kafka 4.0 What's New — Jackson 3 Support](https://docs.spring.io/spring-kafka/reference/whats-new.html#x40-jackson3-support)
- [StringJsonMessageConverter source (deprecated)](https://github.com/spring-projects/spring-kafka/blob/main/spring-kafka/src/main/java/org/springframework/kafka/support/converter/StringJsonMessageConverter.java)
- [StringJacksonJsonMessageConverter source](https://github.com/spring-projects/spring-kafka/blob/main/spring-kafka/src/main/java/org/springframework/kafka/support/converter/StringJacksonJsonMessageConverter.java)
- [JacksonJsonMessageConverter source](https://github.com/spring-projects/spring-kafka/blob/main/spring-kafka/src/main/java/org/springframework/kafka/support/converter/JacksonJsonMessageConverter.java)

## Caveats / Not Found

- No breaking behavioral differences found for the deserialization use case (no-header JSON string -> typed DTO). The `TypePrecedence.INFERRED` default is unchanged.
- The `JsonMapper` constructor accepts `tools.jackson.databind.json.JsonMapper`, not `com.fasterxml.jackson.databind.ObjectMapper`. If the project passes a custom `ObjectMapper`, it must be converted to `JsonMapper`.
- The project currently uses no custom ObjectMapper in the converter (default constructor), so the migration is a simple 1-line import + 1-line instantiation change.
