package ru.team42.monolith.mapper;

import org.mapstruct.*;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.kanban.YouGileService;

@Mapper(componentModel = "spring", unmappedSourcePolicy = ReportingPolicy.IGNORE)
public interface YouGileTaskMapper {

    @BeanMapping(nullValuePropertyMappingStrategy = NullValuePropertyMappingStrategy.IGNORE)
    @Mapping(source = "id", target = "externalId")
    @Mapping(source = "columnId", target = "externalColumnId")
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "createdAt", ignore = true)
    @Mapping(target = "updatedAt", ignore = true)
    @Mapping(target = "team", ignore = true)
    @Mapping(target = "assignee", ignore = true)
    @Mapping(target = "author", ignore = true)
    @Mapping(target = "status", ignore = true)
    @Mapping(target = "syncStatus", ignore = true)
    @Mapping(target = "yougileStatus", ignore = true)
    @Mapping(target = "localStatus", ignore = true)
    @Mapping(target = "source", ignore = true)
    @Mapping(target = "deadline", ignore = true)
    @Mapping(target = "deleted", ignore = true)
    @Mapping(target = "description", ignore = true)
    void apply(YouGileService.YouGileTaskResponse remote, @MappingTarget Task task);
}
