package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.dto.request.CreateKanbanBoardRequest;
import ru.team42.monolith.dto.response.KanbanBoardResponse;
import ru.team42.monolith.entity.Group;
import ru.team42.monolith.entity.KanbanBoard;
import ru.team42.monolith.repository.GroupRepository;
import ru.team42.monolith.repository.KanbanBoardRepository;

import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class KanbanBoardService {

    private final KanbanBoardRepository boardRepository;
    private final GroupRepository groupRepository;

    @Transactional
    public KanbanBoardResponse create(CreateKanbanBoardRequest request) {
        KanbanBoard board = new KanbanBoard();
        board.setName(request.name());
        board.setProvider(request.provider());
        board.setExternalBoardId(request.externalBoardId());
        board.setAccessToken(request.accessToken());
        board.setStatusMappingsJson(request.statusMappingsJson());

        KanbanBoard saved = boardRepository.save(board);

        // FK lives on Group, so we update the group to point to this board
        if (request.groupId() != null) {
            Group group = groupRepository.findById(request.groupId())
                    .orElseThrow(() -> AppException.notFound("Group %s not found".formatted(request.groupId())));
            group.setBoard(saved);
            groupRepository.save(group);
        }

        return KanbanBoardResponse.from(saved);
    }

    @Transactional(readOnly = true)
    public KanbanBoardResponse getById(UUID id) {
        return boardRepository.findById(id)
                .map(KanbanBoardResponse::from)
                .orElseThrow(() -> AppException.notFound("KanbanBoard %s not found".formatted(id)));
    }

    @Transactional(readOnly = true)
    public List<KanbanBoardResponse> listActive() {
        return boardRepository.findAllByActiveTrue().stream()
                .map(KanbanBoardResponse::from)
                .toList();
    }

    @Transactional(readOnly = true)
    public KanbanBoard getEntityById(UUID id) {
        return boardRepository.findById(id)
                .orElseThrow(() -> AppException.notFound("KanbanBoard %s not found".formatted(id)));
    }
}
