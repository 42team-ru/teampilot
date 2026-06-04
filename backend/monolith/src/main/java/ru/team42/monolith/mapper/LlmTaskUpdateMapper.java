package ru.team42.monolith.mapper;

import org.mapstruct.*;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.event.LlmUpdateTaskEvent;

import java.time.Instant;

@Mapper(componentModel = "spring")
public interface LlmTaskUpdateMapper {

    @BeanMapping(nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    @Mapping(source = "titleTask", target = "title")
    @Mapping(target = "deadline", expression = "java(mapDeadline(event))")
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "createdAt", ignore = true)
    @Mapping(target = "updatedAt", ignore = true)
    @Mapping(target = "team", ignore = true)
    @Mapping(target = "assignee", ignore = true)
    @Mapping(target = "author", ignore = true)
    @Mapping(target = "syncStatus", ignore = true)
    @Mapping(target = "externalId", ignore = true)
    @Mapping(target = "column", ignore = true)
    @Mapping(target = "source", ignore = true)
    @Mapping(target = "localStatus", ignore = true)
    void updateTaskFromEvent(LlmUpdateTaskEvent event, @MappingTarget Task task);

    default Instant mapDeadline(LlmUpdateTaskEvent event) {
        if (event.getDeadline() == null || event.getDeadline().getDeadline() == null) {
            return null;
        }
        return Instant.ofEpochMilli(event.getDeadline().getDeadline());
    }
}
