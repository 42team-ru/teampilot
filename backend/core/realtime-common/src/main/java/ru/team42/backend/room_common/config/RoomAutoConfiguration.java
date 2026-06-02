package ru.team42.backend.room_common.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.context.annotation.Lazy;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.scheduling.TaskScheduler;
import org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler;
import ru.team42.backend.room_common.handler.RoomHandler;
import ru.team42.backend.room_common.interceptor.RoomChannelInterceptor;
import ru.team42.backend.room_common.interceptor.RoomHandshakeInterceptor;
import ru.team42.backend.room_common.internal.RoomRegistry;

@AutoConfiguration
@ConditionalOnClass(SimpMessagingTemplate.class)
@EnableConfigurationProperties(RoomProperties.class)
@Import({RoomWebSocketConfig.class, RoomChannelOnlyConfig.class})
public class RoomAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public RoomHandshakeInterceptor roomHandshakeInterceptor() {
        return new RoomHandshakeInterceptor();
    }

    @Bean("roomTaskScheduler")
    public TaskScheduler roomTaskScheduler() {
        ThreadPoolTaskScheduler scheduler = new ThreadPoolTaskScheduler();
        scheduler.setPoolSize(4);
        scheduler.setThreadNamePrefix("room-scheduler-");
        scheduler.initialize();
        return scheduler;
    }

    @Bean
    @ConditionalOnMissingBean
    public RoomRegistry roomRegistry(@Lazy SimpMessagingTemplate messagingTemplate,
                                     @Qualifier("roomTaskScheduler") TaskScheduler taskScheduler,
                                     ObjectProvider<ObjectMapper> objectMapperProvider) {
        return new RoomRegistry(messagingTemplate, taskScheduler,
                objectMapperProvider.getIfAvailable(ObjectMapper::new));
    }

    @Bean
    @ConditionalOnMissingBean
    public RoomChannelInterceptor roomChannelInterceptor(RoomRegistry registry,
                                                          ObjectProvider<ObjectMapper> objectMapperProvider,
                                                          RoomProperties properties) {
        return new RoomChannelInterceptor(registry,
                objectMapperProvider.getIfAvailable(ObjectMapper::new), properties);
    }

    @Bean
    public Object roomHandlerRegistrar(RoomRegistry registry,
                                        ObjectProvider<RoomHandler<?>> handlers) {
        return (org.springframework.beans.factory.SmartInitializingSingleton)
                () -> handlers.forEach(registry::register);
    }
}
