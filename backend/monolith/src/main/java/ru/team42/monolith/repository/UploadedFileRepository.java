package ru.team42.monolith.repository;

import ru.team42.backend.s3_common.repository.AbstractStoredFileRepository;
import ru.team42.monolith.entity.UploadedFile;

import java.util.List;

public interface UploadedFileRepository extends AbstractStoredFileRepository<UploadedFile> {

    List<UploadedFile> findByTelegramUserId(Long userId);

    List<UploadedFile> findByTelegramChatId(Long chatId);
}
