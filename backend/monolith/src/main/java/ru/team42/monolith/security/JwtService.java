package ru.team42.monolith.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import ru.team42.monolith.config.AppProperties;
import ru.team42.monolith.entity.User;

import javax.crypto.SecretKey;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Base64;
import java.util.Date;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class JwtService {

    private final AppProperties appProperties;

    public String generateToken(User user) {
        var jwt = appProperties.getJwt();
        return Jwts.builder()
                .subject(user.getId().toString())
                .claim("telegramId", user.getTelegramId())
                .claim("role", user.getSystemRole().name())
                .issuedAt(new Date())
                .expiration(Date.from(Instant.now().plus(jwt.getExpirationDays(), ChronoUnit.DAYS)))
                .signWith(signingKey())
                .compact();
    }

    public Optional<Claims> validateToken(String token) {
        try {
            return Optional.of(
                    Jwts.parser()
                            .verifyWith(signingKey())
                            .build()
                            .parseSignedClaims(token)
                            .getPayload()
            );
        } catch (JwtException | IllegalArgumentException e) {
            return Optional.empty();
        }
    }

    private SecretKey signingKey() {
        byte[] keyBytes = Base64.getDecoder().decode(appProperties.getJwt().getSecret());
        return Keys.hmacShaKeyFor(keyBytes);
    }
}
