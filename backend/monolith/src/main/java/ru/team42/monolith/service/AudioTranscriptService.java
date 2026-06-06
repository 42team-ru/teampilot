package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import ru.team42.backend.s3_common.config.S3Properties;
import ru.team42.backend.s3_common.service.S3Service;
import ru.team42.monolith.kafka.publisher.TranscriptEventPublisher;

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
    private final AudioConverter audioConverter;
    private final TranscriptEventPublisher transcriptEventPublisher;

    @Async
    public void transcribeAsync(UUID fileId, byte[] audioBytes, String filename, String teamId) {
        try {
            byte[] wavBytes;
            try {
                wavBytes = audioConverter.toWhisperWav(audioBytes);
                log.info("Audio converted to 16kHz WAV for fileId={}", fileId);
            } catch (Exception e) {
                log.warn("Audio conversion failed for fileId={}, sending original bytes: {}", fileId, e.getMessage(), e);
                wavBytes = audioBytes;
            }
            String text = whisperService.transcribe(wavBytes, filename.endsWith(".wav") ? filename : filename + ".wav");
            String key = save(fileId, text);
            transcriptEventPublisher.publishTranscriptReady(fileId, teamId, s3Properties.getDefaultBucket(), key);
        } catch (Exception e) {
            log.error("Whisper transcription failed for fileId={}", fileId, e);
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
