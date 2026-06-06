package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.YouGileStickerState;

import java.util.Optional;
import java.util.UUID;

public interface YouGileStickerStateRepository extends JpaRepository<YouGileStickerState, UUID> {

    Optional<YouGileStickerState> findByStickerIdAndYougileStateId(UUID stickerId, String yougileStateId);
}
