package ru.team42.monolith.security;

import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import ru.team42.monolith.config.AppProperties;
import ru.team42.monolith.dto.request.TelegramOAuthRequest;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.HexFormat;
import java.util.Map;
import java.util.TreeMap;

@Component
@RequiredArgsConstructor
public class TelegramOAuthVerifier {

    private static final long MAX_AUTH_AGE_SECONDS = 86_400L;

    private final AppProperties appProperties;

    public boolean verify(TelegramOAuthRequest req) {
        String botToken = appProperties.getTelegram().getBotToken();
        if (botToken == null || botToken.isBlank()) {
            return false;
        }
        if (isExpired(req.authDate())) {
            return false;
        }
        String dataCheckString = buildDataCheckString(req);
        String expected = hmacHex(dataCheckString, sha256(botToken));
        return expected.equalsIgnoreCase(req.hash());
    }

    private boolean isExpired(long authDate) {
        return Instant.now().getEpochSecond() - authDate > MAX_AUTH_AGE_SECONDS;
    }

    private String buildDataCheckString(TelegramOAuthRequest req) {
        Map<String, String> fields = new TreeMap<>();
        fields.put("id", String.valueOf(req.id()));
        fields.put("auth_date", String.valueOf(req.authDate()));
        if (req.firstName() != null) fields.put("first_name", req.firstName());
        if (req.lastName() != null)  fields.put("last_name", req.lastName());
        if (req.username() != null)  fields.put("username", req.username());
        if (req.photoUrl() != null)  fields.put("photo_url", req.photoUrl());

        var sb = new StringBuilder();
        fields.forEach((k, v) -> {
            if (!sb.isEmpty()) sb.append('\n');
            sb.append(k).append('=').append(v);
        });
        return sb.toString();
    }

    private static byte[] sha256(String input) {
        try {
            return MessageDigest.getInstance("SHA-256")
                    .digest(input.getBytes(StandardCharsets.UTF_8));
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    private static String hmacHex(String data, byte[] key) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(key, "HmacSHA256"));
            return HexFormat.of().formatHex(mac.doFinal(data.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }
}
