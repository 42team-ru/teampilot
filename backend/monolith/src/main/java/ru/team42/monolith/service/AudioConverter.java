package ru.team42.monolith.service;

import org.springframework.stereotype.Service;

import javax.sound.sampled.AudioFormat;
import javax.sound.sampled.AudioInputStream;
import javax.sound.sampled.AudioSystem;
import javax.sound.sampled.UnsupportedAudioFileException;
import java.io.BufferedInputStream;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;

@Service
public class AudioConverter {

    private static final AudioFormat WHISPER_FORMAT = new AudioFormat(
            AudioFormat.Encoding.PCM_SIGNED,
            16000f, // 16 kHz
            16,     // 16-bit
            1,      // mono
            2,      // frame size = 1 channel * 2 bytes
            16000f,
            false   // little-endian
    );

    // whisper.cpp requires 16kHz mono 16-bit PCM WAV
    public byte[] toWhisperWav(byte[] inputBytes) throws IOException, UnsupportedAudioFileException {
        try (var bais = new BufferedInputStream(new ByteArrayInputStream(inputBytes));
             var source = AudioSystem.getAudioInputStream(bais)) {

            AudioFormat sourceFormat = source.getFormat();

            // If compressed (mp3, alaw, ulaw…) — decode to PCM first
            AudioInputStream pcm = source;
            if (!isPcm(sourceFormat)) {
                var decodedFormat = new AudioFormat(
                        AudioFormat.Encoding.PCM_SIGNED,
                        sourceFormat.getSampleRate(),
                        16,
                        sourceFormat.getChannels(),
                        sourceFormat.getChannels() * 2,
                        sourceFormat.getSampleRate(),
                        false
                );
                pcm = AudioSystem.getAudioInputStream(decodedFormat, source);
            }

            try (var converted = AudioSystem.getAudioInputStream(WHISPER_FORMAT, pcm);
                 var out = new ByteArrayOutputStream()) {
                AudioSystem.write(converted, javax.sound.sampled.AudioFileFormat.Type.WAVE, out);
                return out.toByteArray();
            }
        }
    }

    private static boolean isPcm(AudioFormat fmt) {
        return fmt.getEncoding() == AudioFormat.Encoding.PCM_SIGNED
                || fmt.getEncoding() == AudioFormat.Encoding.PCM_UNSIGNED;
    }
}
