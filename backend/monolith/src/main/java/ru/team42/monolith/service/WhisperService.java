package ru.team42.monolith.service;

import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.web.client.RestClient;
import ru.team42.monolith.config.WhisperProperties;

@Service
public class WhisperService {

    private record WhisperResponse(String text) {}

    private final RestClient restClient;
    private final WhisperProperties props;

    public WhisperService(WhisperProperties props) {
        this.props = props;
        this.restClient = RestClient.builder()
                .baseUrl(props.getBaseUrl())
                .build();
    }

    public String transcribe(byte[] audioBytes, String filename) {
        var body = new LinkedMultiValueMap<String, Object>();
        body.add("file", new ByteArrayResource(audioBytes) {
            @Override
            public String getFilename() { return filename; }
        });
        body.add("temperature", "0.0");
        body.add("response_format", "json");
        if (!"/inference".equals(props.getEndpoint())) {
            body.add("model", props.getModel());
        }

        return restClient.post()
                .uri(props.getEndpoint())
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(body)
                .retrieve()
                .body(WhisperResponse.class)
                .text();
    }
}
