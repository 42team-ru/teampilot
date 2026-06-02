package ru.team42.monolith.security;

import org.springframework.security.oauth2.jwt.Jwt;
import ru.team42.monolith.entity.User;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.oauth2.core.user.OAuth2User;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.UUID;


@RequiredArgsConstructor
public final class AuthUserPrincipal implements UserDetails, OAuth2User {

    private final UUID id;
    private final String username;
    private final String passwordHash;
    private final List<User.UserRole> userRoles;
    private final boolean active;
    private final boolean emailVerified;
    private final Map<String, Object> oauthAttributes;

    public static AuthUserPrincipal of(User user) {
        return new AuthUserPrincipal(
                user.getId(), user.getUsername(), user.getPasswordHash(),
                user.getRoles(), user.isActive(), user.isEmailVerified(),
                Map.of()
        );
    }

    public static AuthUserPrincipal ofOAuth2(User user, Map<String, Object> attrs) {
        return new AuthUserPrincipal(
                user.getId(), user.getUsername(), user.getPasswordHash(),
                user.getRoles(), user.isActive(), user.isEmailVerified(),
                Map.copyOf(attrs)
        );
    }

    public UUID getId() { return id; }

    // ── UserDetails ──────────────────────────────────────────────────────────

    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        return userRoles.stream()
                .map(r -> new SimpleGrantedAuthority("ROLE_" + r.name()))
                .toList();
    }

    @Override public String getPassword()              { return passwordHash; }
    @Override public String getUsername()              { return username; }
    @Override public boolean isAccountNonExpired()     { return active; }
    @Override public boolean isAccountNonLocked()      { return emailVerified; }
    @Override public boolean isCredentialsNonExpired() { return active; }
    @Override public boolean isEnabled()               { return active; }

    // ── OAuth2User ───────────────────────────────────────────────────────────

    @Override public Map<String, Object> getAttributes() { return oauthAttributes; }
    @Override public String getName()                    { return username; }

    public static AuthUserPrincipal fromJwt(Jwt jwt) {
        List<User.UserRole> roles = jwt.getClaimAsStringList("roles").stream()
                .map(r -> r.replace("ROLE_", ""))
                .map(User.UserRole::valueOf)
                .toList();

        return new AuthUserPrincipal(
                UUID.fromString(jwt.getSubject()),
                jwt.getClaimAsString("username"),
                null,
                roles,
                true,
                true,
                Map.of()
        );
    }
}
