package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.monolith.event.FileUploadedEvent;
import ru.team42.monolith.entity.UploadedFile;
import ru.team42.monolith.repository.TeamUserRepository;
import ru.team42.monolith.repository.UploadedFileRepository;

@Service
@RequiredArgsConstructor
public class FileUploadService {

    private final UploadedFileRepository uploadedFileRepository;
    private final TeamUserRepository teamUserRepository;

    @Transactional
    public UploadedFile save(FileUploadedEvent event) {
        var existing = uploadedFileRepository.findByS3Key(event.getS3Key());
        if (existing.isPresent()) {
            return existing.get();
        }

        var uploadedFile = new UploadedFile();
        uploadedFile.setBucket(event.getBucket());
        uploadedFile.setS3Key(event.getS3Key());
        uploadedFile.setOriginalFilename(event.getOriginalFilename());
        uploadedFile.setContentType(event.getContentType());
        uploadedFile.setSizeBytes(event.getFileSize());

        if (event.getChatId() != null && event.getUserId() != null) {
            teamUserRepository
                    .findByTeamTelegramChatIdAndUserTelegramId(event.getChatId(), event.getUserId())
                    .ifPresent(uploadedFile::setTeamUser);
        }

        return uploadedFileRepository.save(uploadedFile);
    }
}
