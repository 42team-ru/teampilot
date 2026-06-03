package ru.team42.monolith.config;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import ru.team42.monolith.client.yougile.ApiClient;
import ru.team42.monolith.client.yougile.api.DefaultApi;

@Configuration
public class YougileClientConfig {

    private static final String BASE_PATH = "https://yougile.com";

    /** NON_NULL mapper so optional fields are not serialized as null. */
    public static ApiClient createApiClient() {
        ObjectMapper mapper = ApiClient.createDefaultMapper(null);
        mapper.setSerializationInclusion(JsonInclude.Include.NON_NULL);
        ApiClient client = new ApiClient(mapper, null);
        client.setBasePath(BASE_PATH);
        return client;
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
