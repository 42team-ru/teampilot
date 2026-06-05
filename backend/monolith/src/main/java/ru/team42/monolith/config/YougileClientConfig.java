package ru.team42.monolith.config;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonToken;
import com.fasterxml.jackson.databind.DeserializationContext;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.deser.std.StdDeserializer;
import com.fasterxml.jackson.databind.module.SimpleModule;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import ru.team42.monolith.client.yougile.ApiClient;
import ru.team42.monolith.client.yougile.api.DefaultApi;

import java.io.IOException;

@Configuration
public class YougileClientConfig {

    private static final String BASE_PATH = "https://yougile.com";

    /** NON_NULL mapper so optional fields are not serialized as null. */
    public static ApiClient createApiClient() {
        ObjectMapper mapper = ApiClient.createDefaultMapper(null);
        mapper.setSerializationInclusion(JsonInclude.Include.NON_NULL);
        // YouGile occasionally returns Object/Array where String is expected (e.g. rich-text description).
        // Skip the token tree and return null instead of throwing a deserialization error.
        mapper.registerModule(lenientStringModule());
        ApiClient client = new ApiClient(mapper, null);
        client.setBasePath(BASE_PATH);
        return client;
    }

    private static SimpleModule lenientStringModule() {
        var module = new SimpleModule();
        module.addDeserializer(String.class, new StdDeserializer<>(String.class) {
            @Override
            public String deserialize(JsonParser p, DeserializationContext ctxt) throws IOException {
                if (p.currentToken() == JsonToken.START_OBJECT || p.currentToken() == JsonToken.START_ARRAY) {
                    p.skipChildren();
                    return null;
                }
                return p.getValueAsString();
            }
        });
        return module;
    }

    public static DefaultApi createAuthenticatedApi(String apiKey) {
        ApiClient client = createApiClient();
        client.setBearerToken(apiKey);
        return new DefaultApi(client);
    }

    @Bean
    public DefaultApi yougileUnauthenticatedApi() {
        return new DefaultApi(createApiClient());
    }
}
