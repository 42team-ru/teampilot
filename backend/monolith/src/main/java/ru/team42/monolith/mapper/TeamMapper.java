package ru.team42.monolith.mapper;

import org.mapstruct.Mapper;
import ru.team42.monolith.dto.response.TeamResponse;
import ru.team42.monolith.entity.Team;

@Mapper(componentModel = "spring")
public interface TeamMapper {

    TeamResponse toResponse(Team team);
}
