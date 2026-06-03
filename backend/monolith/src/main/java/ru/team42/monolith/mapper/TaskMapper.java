package ru.team42.monolith.mapper;

import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import ru.team42.monolith.dto.request.CreateTaskRequest;
import ru.team42.monolith.entity.KanbanBoard;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.User;

@Mapper(componentModel = "spring")
public interface TaskMapper {

    // MapStruct matches parameter names to target field names:
    // creator -> task.creator, assignee -> task.assignee, board -> task.board
    // Scalars (title, description, deadline, chatId, sourceContext, priority) matched by name from request.
    @Mapping(target = "id", ignore = true)
    @Mapping(target = "createdAt", ignore = true)
    @Mapping(target = "updatedAt", ignore = true)
    @Mapping(target = "externalTaskId", ignore = true)
    @Mapping(target = "externalStatus", ignore = true)
    @Mapping(target = "status", expression = "java(ru.team42.monolith.entity.TaskStatus.OPEN)")
    @Mapping(target = "priority", expression = "java(request.priority() != null ? request.priority() : ru.team42.monolith.entity.TaskPriority.MEDIUM)")
    Task toEntity(CreateTaskRequest request, User creator, User assignee, KanbanBoard board);
}
