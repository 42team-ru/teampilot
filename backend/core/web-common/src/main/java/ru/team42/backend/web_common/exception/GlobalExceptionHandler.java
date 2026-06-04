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
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
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
import java.util.UUID;

@Slf4j
@Order(Ordered.HIGHEST_PRECEDENCE)
@RestControllerAdvice
public class GlobalExceptionHandler extends ResponseEntityExceptionHandler {

    // ── Custom exceptions ─────────────────────────────────────────────────────

    @ExceptionHandler(AppException.class)
    ResponseEntity<ErrorResponse> onApp(AppException ex, HttpServletRequest req) {
        if (ex.getStatus().is5xxServerError()) log.error("App error: {}", ex.getMessage(), ex);
        else log.debug("[{}] {}", ex.getStatus().value(), ex.getMessage());
        return error(ex.getStatus(), ex.getMessage(), req.getRequestURI());
    }

    @ExceptionHandler(ConstraintViolationException.class)
    ResponseEntity<ValidationErrorResponse> onConstraint(ConstraintViolationException ex, HttpServletRequest req) {
        List<FieldViolation> violations = ex.getConstraintViolations().stream()
                .map(cv -> new FieldViolation(cv.getPropertyPath().toString(), cv.getMessage()))
                .toList();
        log.debug("Constraint violations on {}: {}", req.getRequestURI(), violations);
        return validationError("Constraint violations", req.getRequestURI(), violations);
    }

    @ExceptionHandler(AuthenticationException.class)
    ResponseEntity<ErrorResponse> onAuthentication(AuthenticationException ex, HttpServletRequest req) {
        return error(
                HttpStatus.UNAUTHORIZED,
                "Authentication failed: provide valid credentials",
                req.getRequestURI()
        );
    }

    @ExceptionHandler(AccessDeniedException.class)
    ResponseEntity<ErrorResponse> onAccessDenied(AccessDeniedException ex, HttpServletRequest req) {
        String detail = ex.getMessage() != null && !"Access Denied".equals(ex.getMessage())
                ? ex.getMessage()
                : "Access denied: authenticated principal does not have permission for this operation";
        return error(HttpStatus.FORBIDDEN, detail, req.getRequestURI());
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    ResponseEntity<ErrorResponse> onTypeMismatch(MethodArgumentTypeMismatchException ex, HttpServletRequest req) {
        String type = ex.getRequiredType() != null ? ex.getRequiredType().getSimpleName() : "unknown";
        return error(HttpStatus.BAD_REQUEST,
                "Parameter '%s' must be of type %s".formatted(ex.getName(), type),
                req.getRequestURI());
    }

    @ExceptionHandler(Exception.class)
    ResponseEntity<ErrorResponse> onUnexpected(Exception ex, HttpServletRequest req) {
        log.error("Unexpected error on {}", req.getRequestURI(), ex);
        return error(HttpStatus.INTERNAL_SERVER_ERROR, "An unexpected error occurred", req.getRequestURI());
    }

    // ── Spring MVC exceptions ─────────────────────────────────────────────────
    // handleMethodArgumentNotValid overridden separately — needs ValidationErrorResponse.
    // All other Spring MVC exceptions fall through to handleExceptionInternal.

    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(
            MethodArgumentNotValidException ex, HttpHeaders headers, HttpStatusCode status, WebRequest req) {
        List<FieldViolation> violations = ex.getBindingResult().getAllErrors().stream()
                .map(e -> {
                    String field = e instanceof FieldError fe ? fe.getField() : e.getObjectName();
                    String msg = e.getDefaultMessage();
                    return new FieldViolation(field, msg != null ? msg : "invalid value");
                })
                .toList();
        String path = extractPath(req);
        log.debug("Validation failed on {}: {}", path, violations);
        return ResponseEntity.badRequest()
                .body(new ValidationErrorResponse(400, "Validation Error", "Request contains invalid data",
                        path, traceId(), violations));
    }

    @Override
    protected ResponseEntity<Object> handleExceptionInternal(
            Exception ex, Object body, HttpHeaders headers, HttpStatusCode status, WebRequest req) {
        HttpStatus httpStatus = HttpStatus.resolve(status.value());
        String title = httpStatus != null ? httpStatus.getReasonPhrase() : "Error";
        String detail = resolveDetail(ex, title);
        String path = extractPath(req);
        if (status.is5xxServerError()) log.error("Server error on {}: {}", path, ex.getMessage(), ex);
        else log.debug("[{}] {} — {}", status.value(), detail, path);
        return ResponseEntity.status(status).headers(headers)
                .body(new ErrorResponse(status.value(), title, detail, path, traceId()));
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private ResponseEntity<ErrorResponse> error(HttpStatus status, String detail, String path) {
        return ResponseEntity.status(status)
                .body(new ErrorResponse(status.value(), status.getReasonPhrase(), detail, path, traceId()));
    }

    private ResponseEntity<ValidationErrorResponse> validationError(String detail, String path, List<FieldViolation> violations) {
        return ResponseEntity.badRequest()
                .body(new ValidationErrorResponse(400, "Validation Error", detail, path, traceId(), violations));
    }

    private String resolveDetail(Exception ex, String fallback) {
        return switch (ex) {
            case HttpMessageNotReadableException ignored -> "Request body is malformed or unreadable";
            case MissingServletRequestParameterException e ->
                    "Required parameter '%s' is missing".formatted(e.getParameterName());
            default -> ex.getMessage() != null ? ex.getMessage() : fallback;
        };
    }

    private String traceId() {
        String id = MDC.get("traceId");
        return id != null ? id : UUID.randomUUID().toString().replace("-", "").substring(0, 16);
    }

    private String extractPath(WebRequest req) {
        String desc = req.getDescription(false);
        return desc.startsWith("uri=") ? desc.substring(4) : desc;
    }
}
