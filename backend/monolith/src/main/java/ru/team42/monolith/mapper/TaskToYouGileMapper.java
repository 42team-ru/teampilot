package ru.team42.monolith.mapper;

import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import ru.team42.monolith.client.yougile.model.UpdateDeadline;
import ru.team42.monolith.client.yougile.model.UpdateTaskDto;
import ru.team42.monolith.entity.Task;
import ru.team42.monolith.entity.enums.TaskLocalStatus;

import java.math.BigDecimal;

@Mapper(componentModel = "spring")
public interface TaskToYouGileMapper {

    @Mapping(target = "columnId", source = "column.youGileColumnId")
    @Mapping(target = "completed", constant = "false")
    @Mapping(target = "deleted", expression = "java(task.getLocalStatus() == ru.team42.monolith.entity.enums.TaskLocalStatus.DELETED_FROM_YOUGILE)")
    @Mapping(target = "deadline", expression = "java(mapDeadline(task))")
    @Mapping(target = "assigned", expression = "java(task.getAssignee() != null && task.getAssignee().getYougileUserId() != null ? java.util.List.of(task.getAssignee().getYougileUserId()) : null)")
    @Mapping(target = "archived", ignore = true)
    @Mapping(target = "subtasks", ignore = true)
    @Mapping(target = "timeTracking", ignore = true)
    @Mapping(target = "checklists", ignore = true)
    @Mapping(target = "stickers", source = "stickers")
    @Mapping(target = "color", ignore = true)
    @Mapping(target = "idTaskCommon", ignore = true)
    @Mapping(target = "idTaskProject", ignore = true)
    @Mapping(target = "timer", ignore = true)
    @Mapping(target = "stopwatch", ignore = true)
    @Mapping(target = "deal", ignore = true)
    @Mapping(target = "extensionData", ignore = true)
    UpdateTaskDto toUpdateDto(Task task);

    default UpdateDeadline mapDeadline(Task task) {
        if (task.getDeadline() == null) return null;
        UpdateDeadline dl = new UpdateDeadline();
        dl.setDeadline(BigDecimal.valueOf(task.getDeadline().toEpochMilli()));
        return dl;
    }
}
