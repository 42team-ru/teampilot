package ru.team42.backend.web_common.exception;

import lombok.Getter;
import org.springframework.http.HttpStatus;

@Getter
public class AppException extends RuntimeException {

    private final HttpStatus status;

    private AppException(HttpStatus status, String detail) {
        super(detail);
        this.status = status;
    }

    private AppException(HttpStatus status, String detail, Throwable cause) {
        super(detail, cause);
        this.status = status;
    }

    // ── 4xx ──────────────────────────────────────────────────────────────────

    public static AppException badRequest(String detail) {
        return new AppException(HttpStatus.BAD_REQUEST, detail);
    }

    public static AppException unauthorized(String detail) {
        return new AppException(HttpStatus.UNAUTHORIZED, detail);
    }

    public static AppException forbidden(String detail) {
        return new AppException(HttpStatus.FORBIDDEN, detail);
    }

    public static AppException notFound(String detail) {
        return new AppException(HttpStatus.NOT_FOUND, detail);
    }

    public static AppException alreadyExists(String detail) {
        return new AppException(HttpStatus.CONFLICT, detail);
    }

    // ── 5xx ──────────────────────────────────────────────────────────────────

    public static AppException internalError(String detail) {
        return new AppException(HttpStatus.INTERNAL_SERVER_ERROR, detail);
    }

    public static AppException internalError(String detail, Throwable cause) {
        return new AppException(HttpStatus.INTERNAL_SERVER_ERROR, detail, cause);
    }
}
