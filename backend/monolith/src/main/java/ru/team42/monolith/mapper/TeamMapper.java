package ru.team42.monolith.mapper;

import org.mapstruct.Mapper;
import ru.team42.monolith.dto.response.TeamMemberResponse;
import ru.team42.monolith.dto.response.TeamResponse;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.TeamUser;

@Mapper(componentModel = "spring")
public interface TeamMapper {

    TeamResponse toResponse(Team team);

    default TeamMemberResponse toMemberResponse(TeamUser tu) {
        return new TeamMemberResponse(
                tu.getId(),
                tu.getUser().getTelegramId(),
                tu.getUser().getTelegramLogin(),
                tu.getUser().getFirstName(),
                tu.getUser().getLastName(),
                tu.getRole()
        );
    }
}
