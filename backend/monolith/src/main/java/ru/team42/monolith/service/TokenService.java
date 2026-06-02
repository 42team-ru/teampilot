package ru.team42.monolith.service;

import org.springframework.security.oauth2.jwt.*;
import ru.team42.monolith.dto.DeviceType;
import ru.team42.monolith.dto.RefreshRequest;
import ru.team42.monolith.dto.TokenPair;
import ru.team42.monolith.dto.TokenResponse;
import ru.team42.monolith.entity.RefreshToken;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.repository.RefreshTokenRepository;
import jakarta.servlet.http.Cookie;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseCookie;
import org.springframework.security.crypto.keygen.KeyGenerators;
import org.springframework.security.crypto.keygen.StringKeyGenerator;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.security.AuthUserPrincipal;

import java.net.URI;
import java.time.Instant;
import java.util.Arrays;
import java.util.List;

@Service
@Slf4j
@RequiredArgsConstructor
public class TokenService {

    public static final String REFRESH_TOKEN_COOKIE = "refresh_token";
    public static final String ACCESS_TOKEN_COOKIE  = "access_token";

    private final JwtEncoder jwtEncoder;
    private final JwtDecoder jwtDecoder;
    private final RefreshTokenRepository refreshTokenRepository;

    private final StringKeyGenerator tokenGenerator = KeyGenerators.string();

    @Value("${jwt.access-token-ttl:900}")
    private long accessTokenTtlSeconds;

    @Value("${jwt.refresh-token-ttl:2592000}")
    private long refreshTokenTtlSeconds;

    @Value("${cookie.secure:false}")
    private Boolean secure;

    @Value("${cookie.sameSite:Lax}")
    private String sameSite;

    @Value("${jwt.issuer}")
    private String issuer;

    public AuthUserPrincipal parseToken(String token) {
        Jwt jwt = jwtDecoder.decode(token);
        return AuthUserPrincipal.fromJwt(jwt);
    }

    public TokenPair generateTokenPair(User user) {
        String accessToken  = generateAccessToken(user);
        String refreshToken = generateRefreshToken(user);
        return new TokenPair(accessToken, refreshToken);
    }

    public TokenResponse buildTokenResponse(User user, TokenPair tokenPair, DeviceType deviceType) {
        List<String> roles = user.getRoles().stream()
                .map(r -> "ROLE_" + r.name())
                .toList();

        TokenResponse.TokenResponseBuilder builder = TokenResponse.builder()
                .userId(user.getId().toString())
                .username(user.getUsername())
                .email(user.getEmail())
                .firstName(user.getFirstName())
                .lastName(user.getLastName())
                .roles(roles);

        if (deviceType == DeviceType.MOBILE) {
            builder.accessToken(tokenPair.accessToken())
                    .refreshToken(tokenPair.refreshToken())
                    .expiresIn(accessTokenTtlSeconds)
                    .tokenType("Bearer");
        } else {
            builder.expiresIn(accessTokenTtlSeconds).tokenType("");
        }

        return builder.build();
    }

    public void setTokenCookies(HttpServletResponse response, TokenPair tokenPair, HttpServletRequest request) {
        addCookie(response, REFRESH_TOKEN_COOKIE, tokenPair.refreshToken(), (int) refreshTokenTtlSeconds, request);
        addCookie(response, ACCESS_TOKEN_COOKIE,  tokenPair.accessToken(),  (int) accessTokenTtlSeconds,  request);
    }

    public void clearTokenCookies(HttpServletResponse response, HttpServletRequest request) {
        addCookie(response, REFRESH_TOKEN_COOKIE, "", 0, request);
        addCookie(response, ACCESS_TOKEN_COOKIE,  "", 0, request);
    }

    @Transactional
    public String validateAndRotateRefreshToken(HttpServletRequest request, HttpServletResponse response,
                                                String tokenValue) {
        RefreshToken token = refreshTokenRepository.findById(tokenValue).orElse(null);
        if (token == null || token.isExpired()) {
            if (token != null) refreshTokenRepository.deleteById(tokenValue);
            clearTokenCookies(response, request);
            log.warn("Refresh token не найден или истёк");
            throw AppException.unauthorized("Невалидный или истёкший refresh token");
        }
        refreshTokenRepository.deleteById(tokenValue);
        return token.getUsername();
    }

    public void revokeRefreshToken(String tokenValue) {
        if (tokenValue != null && !tokenValue.isBlank()) {
            refreshTokenRepository.deleteById(tokenValue);
        }
    }

    public String extractRefreshToken(HttpServletRequest request, RefreshRequest body) {
        if (request.getCookies() != null) {
            return Arrays.stream(request.getCookies())
                    .filter(c -> REFRESH_TOKEN_COOKIE.equals(c.getName()))
                    .map(Cookie::getValue)
                    .findFirst()
                    .orElse(body != null ? body.getRefreshToken() : null);
        }
        return body != null ? body.getRefreshToken() : null;
    }

    public DeviceType detectDeviceType(HttpServletRequest request) {
        if (request.getCookies() != null) {
            boolean hasCookie = Arrays.stream(request.getCookies())
                    .anyMatch(c -> REFRESH_TOKEN_COOKIE.equals(c.getName()));
            if (hasCookie) return DeviceType.WEB;
        }
        return DeviceType.MOBILE;
    }

    private String generateAccessToken(User user) {
        Instant now = Instant.now();
        List<String> roles = user.getRoles().stream()
                .map(r -> "ROLE_" + r.name())
                .toList();

        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer(issuer)
                .subject(user.getId().toString())
                .issuedAt(now)
                .expiresAt(now.plusSeconds(accessTokenTtlSeconds))
                .claim("username",  user.getUsername())
                .claim("email",     user.getEmail())
                .claim("firstName", user.getFirstName())
                .claim("lastName",  user.getLastName())
                // Исправление: claim "roles" совпадает с authoritiesClaimName в SecurityConfig
                .claim("roles", roles)
                .build();

        return jwtEncoder.encode(JwtEncoderParameters.from(claims)).getTokenValue();
    }

    private String generateRefreshToken(User user) {
        String tokenValue = tokenGenerator.generateKey();
        RefreshToken token = RefreshToken.builder()
                .tokenValue(tokenValue)
                .userId(user.getId())
                .username(user.getUsername())
                .expiresAt(Instant.now().plusSeconds(refreshTokenTtlSeconds))
                .build();
        refreshTokenRepository.save(token);
        return tokenValue;
    }

    private void addCookie(HttpServletResponse response, String name, String value, int maxAge,
                           HttpServletRequest request) {
        boolean crossOrigin     = isCrossOrigin(request);
        String effectiveSameSite = crossOrigin ? "None" : sameSite;
        boolean effectiveSecure  = crossOrigin || secure;

        ResponseCookie.ResponseCookieBuilder builder = ResponseCookie.from(name, value)
                .maxAge(maxAge)
                .path("/")
                .httpOnly(true)
                .secure(effectiveSecure)
                .sameSite(effectiveSameSite);

        String cookieDomain = extractDomain(request);
        if (cookieDomain != null && !cookieDomain.isBlank()) {
            builder.domain(cookieDomain);
        }

        log.info("Set cookie: name={}, domain={}, maxAge={}, secure={}, sameSite={}",
                name, cookieDomain, maxAge, effectiveSecure, effectiveSameSite);

        response.addHeader(HttpHeaders.SET_COOKIE, builder.build().toString());
    }

    private boolean isCrossOrigin(HttpServletRequest request) {
        String origin = request.getHeader("Origin");
        if (origin == null || origin.isBlank()) return false;
        try {
            String originHost = new URI(origin).getHost();
            return originHost != null && !originHost.equals(request.getServerName());
        } catch (Exception e) {
            return false;
        }
    }

    private String extractDomain(HttpServletRequest request) {
        String origin = request.getHeader("Origin");
        if (origin != null && !origin.isBlank()) {
            try {
                String host = new URI(origin).getHost();
                return isLocalHost(host) ? null : host;
            } catch (Exception e) {
                log.warn("Не удалось распарсить Origin: {}", origin);
            }
        }
        String serverName = request.getServerName();
        return isLocalHost(serverName) ? null : serverName;
    }

    private boolean isLocalHost(String host) {
        return host == null || host.equals("localhost") || host.equals("127.0.0.1") || host.equals("::1");
    }
}
