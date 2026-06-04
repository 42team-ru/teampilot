package ru.team42.backend.web_common.config;

import io.swagger.v3.core.converter.ModelConverters;
import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.media.Content;
import io.swagger.v3.oas.models.media.MediaType;
import io.swagger.v3.oas.models.media.Schema;
import io.swagger.v3.oas.models.responses.ApiResponse;
import io.swagger.v3.oas.models.responses.ApiResponses;
import org.springdoc.core.customizers.OpenApiCustomizer;
import org.springdoc.core.customizers.OperationCustomizer;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.condition.ConditionalOnWebApplication;
import org.springframework.context.annotation.Bean;
import ru.team42.backend.web_common.dto.ErrorResponse;
import ru.team42.backend.web_common.dto.ValidationErrorResponse;
import ru.team42.backend.web_common.exception.GlobalExceptionHandler;

@AutoConfiguration
@ConditionalOnWebApplication(type = ConditionalOnWebApplication.Type.SERVLET)
public class WebCommonAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public GlobalExceptionHandler globalExceptionHandler() {
        return new GlobalExceptionHandler();
    }

    @Bean
    @ConditionalOnMissingBean(name = "errorSchemasCustomizer")
    @ConditionalOnClass(name = "org.springdoc.core.customizers.OpenApiCustomizer")
    public OpenApiCustomizer errorSchemasCustomizer() {
        return openApi -> {
            Components components = openApi.getComponents();
            if (components == null) {
                components = new Components();
                openApi.setComponents(components);
            }
            Components c = components;
            ModelConverters.getInstance().read(ErrorResponse.class).forEach(c::addSchemas);
            ModelConverters.getInstance().read(ValidationErrorResponse.class).forEach(c::addSchemas);
        };
    }

    @Bean
    @ConditionalOnMissingBean(name = "globalErrorResponses")
    @ConditionalOnClass(name = "org.springdoc.core.customizers.OperationCustomizer")
    public OperationCustomizer globalErrorResponses() {
        return (operation, handlerMethod) -> {
            ApiResponses responses = operation.getResponses();
            if (responses == null) {
                responses = new ApiResponses();
                operation.setResponses(responses);
            }
            addIfAbsent(responses, "400", "Bad request", ErrorResponse.class);
            addIfAbsent(responses, "401", "Unauthorized", ErrorResponse.class);
            addIfAbsent(responses, "403", "Access denied", ErrorResponse.class);
            addIfAbsent(responses, "500", "Internal server error", ErrorResponse.class);
            return operation;
        };
    }

    private void addIfAbsent(ApiResponses responses, String code, String description,
                              Class<?> schemaClass) {
        if (responses.containsKey(code)) return;
        Schema<?> ref = new Schema<>().$ref("#/components/schemas/" + schemaClass.getSimpleName());
        responses.addApiResponse(code, new ApiResponse()
                .description(description)
                .content(new Content().addMediaType(
                        "application/json", new MediaType().schema(ref))));
    }
}
