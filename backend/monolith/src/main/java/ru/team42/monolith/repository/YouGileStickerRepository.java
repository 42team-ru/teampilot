package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import ru.team42.monolith.entity.YouGileSticker;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface YouGileStickerRepository extends JpaRepository<YouGileSticker, UUID> {

    Optional<YouGileSticker> findByTeamIdAndYougileStickerId(UUID teamId, String yougileStickerId);

    @Query("SELECT s FROM YouGileSticker s LEFT JOIN FETCH s.states WHERE s.team.id = :teamId")
    List<YouGileSticker> findByTeamIdWithStates(UUID teamId);
}
