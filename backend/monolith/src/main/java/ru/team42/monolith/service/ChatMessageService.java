package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.monolith.event.ChatMessageEvent;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.entity.enums.TeamRole;
import ru.team42.monolith.mapper.ChatMessageMapper;
import ru.team42.monolith.repository.ChatMessageRepository;
import ru.team42.monolith.repository.TeamRepository;
import ru.team42.monolith.repository.TeamUserRepository;
import ru.team42.monolith.repository.UserRepository;

import java.util.List;
import java.util.Optional;

@Slf4j
@Service
@RequiredArgsConstructor
public class ChatMessageService {

    private final ChatMessageRepository chatMessageRepository;
    private final ChatMessageMapper chatMessageMapper;
    private final UserRepository userRepository;
    private final TeamRepository teamRepository;
    private final TeamUserRepository teamUserRepository;

    @Transactional
    public void saveAll(List<ChatMessageEvent> events) {
        events.forEach(this::save);
    }

    @Transactional
    public void save(ChatMessageEvent event) {
        Optional<TeamUser> teamUserOpt = teamUserRepository
                .findByTeamTelegramChatIdAndUserTelegramId(event.getChatId(), event.getUserId());

        TeamUser teamUser;
        if (teamUserOpt.isPresent()) {
            teamUser = teamUserOpt.get();
        } else {
            Optional<Team> teamOpt = teamRepository.findByTelegramChatIdAndActiveTrue(event.getChatId());
            if (teamOpt.isEmpty()) {
                log.warn("No team found for chatId={}, dropping message", event.getChatId());
                return;
            }
            User user = findOrCreateUser(event);
            var newTeamUser = new TeamUser();
            newTeamUser.setTeam(teamOpt.get());
            newTeamUser.setUser(user);
            newTeamUser.setRole(TeamRole.USER);
            teamUser = teamUserRepository.save(newTeamUser);
        }

        chatMessageRepository.save(chatMessageMapper.toEntity(event, teamUser));
    }

    private User findOrCreateUser(ChatMessageEvent event) {
        return userRepository.findByTelegramId(event.getUserId())
                .orElseGet(() -> {
                    var user = new User();
                    user.setTelegramId(event.getUserId());
                    user.setTelegramLogin(event.getUsername());
                    String[] parts = event.getFullName() != null
                            ? event.getFullName().split(" ", 2)
                            : new String[]{"", null};
                    user.setFirstName(parts[0]);
                    user.setLastName(parts.length > 1 ? parts[1] : null);
                    return userRepository.save(user);
                });
    }
}
