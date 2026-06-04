package ru.team42.monolith.kafka.publisher;

//@Component
//public class AudioEventPublisher extends AbstractEventPublisher {
//
//    public void publishAudioNew(AudioFile audioFile) {
//        var event = AudioNewEvent.builder()
//                .fileId(audioFile.getId())
//                .bucket(audioFile.getBucket())
//                .s3Key(audioFile.getS3Key())
//                .originalFilename(audioFile.getOriginalFilename())
//                .contentType(audioFile.getContentType())
//                .sizeBytes(audioFile.getSizeBytes())
//                .uploadedAt(Instant.now())
//                .build();
//        send(KafkaTopics.AUDIO_NEW, audioFile.getId().toString(), event);
//    }
//}
