package ru.team42.backend.web_common.util;

import org.springframework.http.ResponseEntity;
import ru.team42.backend.web_common.dto.PageResponse;

import java.net.URI;

public final class ResponseUtils {

    private ResponseUtils() {}

    public static <T> ResponseEntity<T> created(String location, T body) {
        return ResponseEntity.created(URI.create(location)).body(body);
    }

    public static ResponseEntity<Void> noContent() {
        return ResponseEntity.noContent().build();
    }

    public static <T> ResponseEntity<PageResponse<T>> page(PageResponse<T> pageResponse) {
        return ResponseEntity.ok(pageResponse);
    }
}
