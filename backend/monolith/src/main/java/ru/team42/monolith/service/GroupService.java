package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.monolith.dto.request.GroupRequest;
import ru.team42.monolith.dto.response.GroupResponse;
import ru.team42.monolith.entity.Group;
import ru.team42.monolith.repository.GroupRepository;

import java.util.Optional;

@Service
@RequiredArgsConstructor
public class GroupService {

    private final GroupRepository groupRepository;

    @Transactional
    public GroupResponse register(GroupRequest req) {
        Group group = groupRepository.findByChatId(req.chatId())
                .orElseGet(Group::new);
        group.setChatId(req.chatId());
        group.setChatTitle(req.chatTitle());
        group.setAddedByTelegramId(req.addedByTelegramId());
        group.setYougileToken(req.yougileToken());
        group.setYougileBoardId(req.yougileBoardId());
        group.setActive(true);
        Group saved = groupRepository.save(group);
        return toResponse(saved);
    }

    public Optional<GroupResponse> findByChatId(Long chatId) {
        return groupRepository.findByChatId(chatId).map(this::toResponse);
    }

    @Transactional
    public void deactivate(Long chatId) {
        groupRepository.findByChatId(chatId).ifPresent(group -> {
            group.setActive(false);
            groupRepository.save(group);
        });
    }

    private GroupResponse toResponse(Group group) {
        return new GroupResponse(
                group.getId(),
                group.getChatId(),
                group.getChatTitle(),
                group.getYougileBoardId(),
                group.isActive()
        );
    }
}
