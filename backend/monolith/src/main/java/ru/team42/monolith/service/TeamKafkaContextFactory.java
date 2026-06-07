package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import ru.team42.monolith.event.AudioNewEvent;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.repository.TaskColumnRepository;
import ru.team42.monolith.repository.TeamUserRepository;
import ru.team42.monolith.repository.YouGileStickerRepository;

import java.util.List;
import java.util.UUID;

@Component
@RequiredArgsConstructor
public class TeamKafkaContextFactory {

    private final TeamUserRepository teamUserRepository;
    private final TaskColumnRepository taskColumnRepository;
    private final YouGileStickerRepository stickerRepository;

    public TeamKafkaContext build(UUID teamId) {
        return new TeamKafkaContext(
                buildMembers(teamId),
                buildColumns(teamId),
                buildStickers(teamId)
        );
    }

    private List<AudioNewEvent.TeamMemberDto> buildMembers(UUID teamId) {
        return teamUserRepository.findByTeamId(teamId).stream()
                .map(this::toMemberDto)
                .toList();
    }

    private List<AudioNewEvent.ColumnDto> buildColumns(UUID teamId) {
        return taskColumnRepository.findByTeamId(teamId).stream()
                .map(col -> AudioNewEvent.ColumnDto.builder()
                        .id(col.getId().toString())
                        .title(col.getTitle())
                        .build())
                .toList();
    }

    private List<AudioNewEvent.StickerDto> buildStickers(UUID teamId) {
        return stickerRepository.findByTeamIdWithStates(teamId).stream()
                .map(s -> AudioNewEvent.StickerDto.builder()
                        .id(s.getYougileStickerId())
                        .title(s.getTitle())
                        .type(s.getType().name())
                        .states(s.getStates().stream()
                                .map(st -> AudioNewEvent.StickerStateDto.builder()
                                        .id(st.getYougileStateId())
                                        .title(st.getTitle())
                                        .build())
                                .toList())
                        .build())
                .toList();
    }

    private AudioNewEvent.TeamMemberDto toMemberDto(TeamUser tu) {
        var user = tu.getUser();
        return AudioNewEvent.TeamMemberDto.builder()
                .telegramId(user.getTelegramId())
                .username(user.getTelegramLogin() != null ? user.getTelegramLogin() : "")
                .fullName(buildFullName(user.getFirstName(), user.getLastName()))
                .role(tu.getRole().name())
                .position(tu.getPosition())
                .build();
    }

    private static String buildFullName(String first, String last) {
        String f = first != null ? first : "";
        String l = last != null ? " " + last : "";
        return (f + l).trim();
    }

    public record TeamKafkaContext(
            List<AudioNewEvent.TeamMemberDto> team,
            List<AudioNewEvent.ColumnDto> columns,
            List<AudioNewEvent.StickerDto> stickers
    ) {
    }
}
