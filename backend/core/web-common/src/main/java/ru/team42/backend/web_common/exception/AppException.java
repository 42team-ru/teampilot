package ru.team42.backend.web_common.exception;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.ErrorResponseException;

public class AppException extends ErrorResponseException {

    public AppException(HttpStatus status, String detail) {
        super(status, ProblemDetail.forStatusAndDetail(status, detail), null);
    }

    public static AppException notFound(String detail) {
        return new AppException(HttpStatus.NOT_FOUND, detail);
    }

    public static AppException alreadyExists(String detail) {
        return new AppException(HttpStatus.CONFLICT, detail);
    }

    public static AppException forbidden(String detail) {
        return new AppException(HttpStatus.FORBIDDEN, detail);
    }

    public static AppException unauthorized(String detail) {
        return new AppException(HttpStatus.UNAUTHORIZED, detail);
    }

    public static AppException badRequest(String detail) {
        return new AppException(HttpStatus.BAD_REQUEST, detail);
    }
}
