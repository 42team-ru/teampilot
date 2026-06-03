package ru.team42.monolith.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import ru.team42.monolith.entity.AudioFile;

import java.util.UUID;

public interface AudioFileRepository extends JpaRepository<AudioFile, UUID> {}
