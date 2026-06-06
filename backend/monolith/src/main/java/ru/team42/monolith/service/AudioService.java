package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import ru.team42.backend.s3_common.config.S3Properties;
import ru.team42.backend.s3_common.service.S3Service;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.dto.response.AudioUploadResponse;
import ru.team42.monolith.entity.AudioFile;
import ru.team42.monolith.repository.AudioFileRepository;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class AudioService {

    private static final String AUDIO_KEY_PREFIX = "audio/";

    private final S3Service s3Service;
    private final S3Properties s3Properties;
    private final AudioFileRepository audioFileRepository;
    private final AudioTranscriptService audioTranscriptService;

    @Transactional
    public AudioUploadResponse upload(MultipartFile file, String teamId) {
        String originalFilename = file.getOriginalFilename() != null
                ? file.getOriginalFilename()
                : file.getName();
        String contentType = file.getContentType() != null
                ? file.getContentType()
                : "application/octet-stream";

        byte[] audioBytes;
        try {
            audioBytes = file.getBytes();
        } catch (IOException e) {
            throw AppException.internalError("Failed to read audio file: " + e.getMessage());
        }

        String bucket = s3Properties.getDefaultBucket();
        String key = AUDIO_KEY_PREFIX + UUID.randomUUID() + "/" + originalFilename;

        s3Service.upload(bucket, key, new ByteArrayInputStream(audioBytes), audioBytes.length, contentType);

        var audioFile = new AudioFile();
        audioFile.setBucket(bucket);
        audioFile.setS3Key(key);
        audioFile.setOriginalFilename(originalFilename);
        audioFile.setContentType(contentType);
        audioFile.setSizeBytes((long) audioBytes.length);
        audioFileRepository.save(audioFile);

        audioTranscriptService.transcribeAsync(audioFile.getId(), audioBytes, originalFilename, teamId);

        return new AudioUploadResponse(
                audioFile.getId(),
                audioFile.getBucket(),
                audioFile.getS3Key(),
                audioFile.getOriginalFilename(),
                audioFile.getSizeBytes()
        );
    }
}
