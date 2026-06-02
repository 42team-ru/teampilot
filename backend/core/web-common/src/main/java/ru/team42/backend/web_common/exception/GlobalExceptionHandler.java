package ru.team42.backend.web_common.exception;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.ConstraintViolationException;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;
import ru.team42.backend.web_common.dto.ErrorResponse;
import ru.team42.backend.web_common.dto.FieldViolation;
import ru.team42.backend.web_common.dto.ValidationErrorResponse;

import java.util.List;

@Slf4j
@Order(Ordered.HIGHEST_PRECEDENCE)
@RestControllerAdvice
public class GlobalExceptionHandler extends ResponseEntityExceptionHandler {

    @ExceptionHandler(AppException.class)
    public ResponseEntity<ErrorResponse> handleAppException(AppException ex, HttpServletRequest request) {
        HttpStatus status = HttpStatus.resolve(ex.getStatusCode().value());
        if (status != null && status.is5xxServerError()) {
            log.error("Application error: {}", ex.getMessage(), ex);
        } else {
            log.debug("Client error [{}]: {}", ex.getStatusCode().value(), ex.getMessage());
        }
        return ResponseEntity.status(ex.getStatusCode()).body(new ErrorResponse(
                ex.getStatusCode().value(),
                status != null ? phrase(status) : "Error",
                ex.getBody().getDetail(),
                request.getRequestURI(),
                traceId()
        ));
    }

    @ExceptionHandler(ConstraintViolationException.class)
    public ResponseEntity<ValidationErrorResponse> handleConstraintViolation(
            ConstraintViolationException ex, HttpServletRequest request) {

        List<FieldViolation> violations = ex.getConstraintViolations().stream()
                .map(cv -> new FieldViolation(cv.getPropertyPath().toString(), cv.getMessage()))
                .toList();
        log.debug("Constraint violations on {}: {}", request.getRequestURI(), violations);
        return ResponseEntity.badRequest().body(new ValidationErrorResponse(
                400, "Validation Error", "Constraint violations",
                request.getRequestURI(), traceId(), violations
        ));
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<ErrorResponse> handleTypeMismatch(
            MethodArgumentTypeMismatchException ex, HttpServletRequest request) {

        String expected = ex.getRequiredType() != null ? ex.getRequiredType().getSimpleName() : "unknown";
        String detail = "Parameter '%s' must be of type %s".formatted(ex.getName(), expected);
        log.debug("Type mismatch on {}: {}", request.getRequestURI(), detail);
        return ResponseEntity.badRequest().body(new ErrorResponse(
                400, "Bad Request", detail, request.getRequestURI(), traceId()
        ));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleUnexpected(Exception ex, HttpServletRequest request) {
        log.error("Unexpected error on {}", request.getRequestURI(), ex);
        return ResponseEntity.internalServerError().body(new ErrorResponse(
                500, "Internal Server Error", "An unexpected error occurred",
                request.getRequestURI(), traceId()
        ));
    }

    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(
            MethodArgumentNotValidException ex, HttpHeaders headers, HttpStatusCode status, WebRequest request) {

        List<FieldViolation> violations = ex.getBindingResult().getAllErrors().stream()
                .map(error -> {
                    String field = error instanceof FieldError fe ? fe.getField() : error.getObjectName();
                    String message = error.getDefaultMessage();
                    return new FieldViolation(field, message != null ? message : "invalid value");
                })
                .toList();
        log.debug("Validation failed on {}: {}", extractPath(request), violations);
        return ResponseEntity.badRequest().body(new ValidationErrorResponse(
                400, "Validation Error", "Request contains invalid data",
                extractPath(request), traceId(), violations
        ));
    }

    @Override
    protected ResponseEntity<Object> handleHttpMessageNotReadable(
            HttpMessageNotReadableException ex, HttpHeaders headers, HttpStatusCode status, WebRequest request) {

        log.debug("Malformed request body on {}: {}", extractPath(request), ex.getMessage());
        return ResponseEntity.badRequest().body(new ErrorResponse(
                400, "Bad Request", "Request body is malformed or unreadable",
                extractPath(request), traceId()
        ));
    }

    @Override
    protected ResponseEntity<Object> handleMissingServletRequestParameter(
            MissingServletRequestParameterException ex, HttpHeaders headers, HttpStatusCode status, WebRequest request) {

        log.debug("Missing parameter '{}' on {}", ex.getParameterName(), extractPath(request));
        return ResponseEntity.badRequest().body(new ErrorResponse(
                400, "Bad Request",
                "Required parameter '" + ex.getParameterName() + "' is missing",
                extractPath(request), traceId()
        ));
    }

    @Override
    protected ResponseEntity<Object> handleExceptionInternal(
            Exception ex, Object body, HttpHeaders headers, HttpStatusCode statusCode, WebRequest request) {

        HttpStatus httpStatus = HttpStatus.resolve(statusCode.value());
        String title = httpStatus != null ? phrase(httpStatus) : "Error";
        return super.handleExceptionInternal(ex,
                new ErrorResponse(statusCode.value(), title, title, extractPath(request), traceId()),
                headers, statusCode, request);
    }

    private String phrase(HttpStatus status) {
        return status.getReasonPhrase();
    }

    private String traceId() {
        return MDC.get("traceId");
    }

    private String extractPath(WebRequest request) {
        String description = request.getDescription(false);
        return description.startsWith("uri=") ? description.substring(4) : description;
    }
}
