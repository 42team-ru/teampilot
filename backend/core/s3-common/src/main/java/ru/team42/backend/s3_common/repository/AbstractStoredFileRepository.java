package ru.team42.backend.s3_common.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.repository.NoRepositoryBean;
import ru.team42.backend.s3_common.entity.AbstractStoredFileEntity;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

/**
 * Базовый репозиторий для работы с метаданными файлов в Postgres.
 *
 * Использование:
 * <pre>{@code
 * @Repository
 * public interface ReportFileRepository
 *         extends AbstractStoredFileRepository<ReportFile> { }
 * }</pre>
 */
@NoRepositoryBean
public interface AbstractStoredFileRepository<T extends AbstractStoredFileEntity>
        extends JpaRepository<T, UUID> {

    /** Найти запись по ключу объекта в S3. */
    Optional<T> findByS3Key(String s3Key);

    /** Все файлы, принадлежащие конкретному пользователю. */
    List<T> findByOwnerId(UUID ownerId);

    Optional<T> findFirstByOwnerId(UUID ownerId);

    /** Все файлы из заданного бакета. */
    List<T> findByBucket(String bucket);

    /** Проверить, есть ли запись с таким ключом в S3. */
    boolean existsByS3Key(String s3Key);

    /** Удалить запись по ключу объекта в S3. */
    void deleteByS3Key(String s3Key);
}
