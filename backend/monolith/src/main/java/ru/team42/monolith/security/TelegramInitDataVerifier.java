package ru.team42.monolith.security;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import ru.team42.monolith.config.AppProperties;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import java.util.TreeMap;

/**
 * Verifies Telegram Mini App initData HMAC-SHA256 signature.
 * Algorithm differs from OAuth widget: secret key is HMAC-SHA256(key="WebAppData", data=botToken).
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class TelegramInitDataVerifier {

    public static final String INIT_DATA_HEADER = "X-Telegram-Init-Data";

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final AppProperties appProperties;

    public boolean verify(String initData) {
        if (initData == null || initData.isBlank()) return false;
        String botToken = appProperties.getTelegram().getBotToken();
        if (botToken == null || botToken.isBlank()) return false;
        try {
            Map<String, String> params = parseParams(initData);
            String hash = params.remove("hash");
            if (hash == null) return false;

            String dataCheckString = buildDataCheckString(params);
            byte[] secretKey = hmac(
                    botToken.getBytes(StandardCharsets.UTF_8),
                    "WebAppData".getBytes(StandardCharsets.UTF_8)
            );
            String expected = HexFormat.of().formatHex(
                    hmac(dataCheckString.getBytes(StandardCharsets.UTF_8), secretKey)
            );
            return expected.equalsIgnoreCase(hash);
        } catch (Exception e) {
            log.warn("initData HMAC verification failed: {}", e.getMessage());
            return false;
        }
    }

    public Optional<TelegramUserInfo> extractUserInfo(String initData) {
        try {
            Map<String, String> params = parseParams(initData);
            String userJson = params.get("user");
            if (userJson == null) return Optional.empty();
            JsonNode node = MAPPER.readTree(userJson);
            long id = node.get("id").asLong();
            String firstName = node.has("first_name") ? node.get("first_name").asText(null) : null;
            String lastName = node.has("last_name") ? node.get("last_name").asText(null) : null;
            String username = node.has("username") ? node.get("username").asText(null) : null;
            return Optional.of(new TelegramUserInfo(id, firstName, lastName, username));
        } catch (Exception e) {
            log.warn("Failed to extract user info from initData: {}", e.getMessage());
            return Optional.empty();
        }
    }

    private Map<String, String> parseParams(String initData) {
        Map<String, String> params = new LinkedHashMap<>();
        for (String part : initData.split("&")) {
            int eq = part.indexOf('=');
            if (eq < 0) continue;
            String key = URLDecoder.decode(part.substring(0, eq), StandardCharsets.UTF_8);
            String value = URLDecoder.decode(part.substring(eq + 1), StandardCharsets.UTF_8);
            params.put(key, value);
        }
        return params;
    }

    private String buildDataCheckString(Map<String, String> params) {
        var sorted = new TreeMap<>(params);
        var sb = new StringBuilder();
        sorted.forEach((k, v) -> {
            if (!sb.isEmpty()) sb.append('\n');
            sb.append(k).append('=').append(v);
        });
        return sb.toString();
    }

    private static byte[] hmac(byte[] data, byte[] key) throws Exception {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(key, "HmacSHA256"));
        return mac.doFinal(data);
    }

    public record TelegramUserInfo(long id, String firstName, String lastName, String username) {}
}
