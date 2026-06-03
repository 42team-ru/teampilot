package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import ru.team42.backend.s3_common.config.S3Properties;
import ru.team42.backend.s3_common.service.S3Service;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class AudioTranscriptService {

    private final S3Service s3Service;
    private final S3Properties s3Properties;
    private final WhisperService whisperService;

    @Async
    public void transcribeAsync(UUID fileId, byte[] audioBytes, String filename) {
        try {
            String text = whisperService.transcribe(audioBytes, filename);
            save(fileId, text);
        } catch (Exception e) {
            log.warn("Whisper transcription failed for fileId={}: {}", fileId, e.getMessage());
        }
    }

    private String save(UUID fileId, String text) {
        byte[] bytes = text.getBytes(StandardCharsets.UTF_8);
        String key = "transcripts/" + fileId + ".txt";

        try (var is = new ByteArrayInputStream(bytes)) {
            s3Service.upload(s3Properties.getDefaultBucket(), key, is, bytes.length, "text/plain; charset=utf-8");
        } catch (IOException e) {
            throw new RuntimeException("Failed to upload transcript", e);
        }

        return key;
    }
}
