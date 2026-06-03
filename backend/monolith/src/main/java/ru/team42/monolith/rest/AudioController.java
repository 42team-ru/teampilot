package ru.team42.monolith.rest;

import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.backend.web_common.util.ResponseUtils;
import ru.team42.monolith.dto.response.AudioUploadResponse;
import ru.team42.monolith.service.AudioService;

@RestController
@RequestMapping("/audio")
@RequiredArgsConstructor
public class AudioController {

    private final AudioService audioService;

    @PostMapping(value = "/upload", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<AudioUploadResponse> upload(
            @RequestParam("file") MultipartFile file
    ) {
        if (file.isEmpty()) {
            throw AppException.badRequest("Audio file is empty");
        }
        var response = audioService.upload(file);
        return ResponseUtils.created("/audio/" + response.fileId(), response);
    }
}
