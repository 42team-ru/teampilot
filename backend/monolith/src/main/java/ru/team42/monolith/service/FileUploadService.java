package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.monolith.event.FileUploadedEvent;
import ru.team42.monolith.entity.UploadedFile;
import ru.team42.monolith.repository.UploadedFileRepository;

@Service
@RequiredArgsConstructor
public class FileUploadService {

    private final UploadedFileRepository uploadedFileRepository;

    @Transactional
    public UploadedFile save(FileUploadedEvent event) {
        var uploadedFile = new UploadedFile();
        uploadedFile.setBucket(event.getBucket());
        uploadedFile.setS3Key(event.getS3Key());
        uploadedFile.setOriginalFilename(event.getOriginalFilename());
        uploadedFile.setContentType(event.getContentType());
        uploadedFile.setSizeBytes(event.getFileSize());
        uploadedFile.setTelegramUserId(event.getUserId());
        uploadedFile.setTelegramChatId(event.getChatId());
        uploadedFile.setTelegramUsername(event.getUsername());
        uploadedFile.setTelegramFirstName(event.getFirstName());
        return uploadedFileRepository.save(uploadedFile);
    }
}
