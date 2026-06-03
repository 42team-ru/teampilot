package ru.team42.monolith.entity;

import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.s3_common.entity.AbstractStoredFileEntity;

@Entity
@Table(name = "audio_files")
@Getter
@Setter
@NoArgsConstructor
public class AudioFile extends AbstractStoredFileEntity {}
