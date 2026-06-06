package ru.team42.monolith.repository;

import ru.team42.backend.s3_common.repository.AbstractStoredFileRepository;
import ru.team42.monolith.entity.UploadedFile;

import java.util.List;
import java.util.UUID;

public interface UploadedFileRepository extends AbstractStoredFileRepository<UploadedFile> {

    List<UploadedFile> findByTeamUser_Id(UUID teamUserId);

    List<UploadedFile> findByTeamUser_Team_TelegramChatId(Long chatId);
}
