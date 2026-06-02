package ru.team42.backend.security_common.filter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.preauth.PreAuthenticatedAuthenticationToken;
import org.springframework.web.filter.OncePerRequestFilter;
import ru.team42.backend.security_common.model.UserPrincipal;

import java.io.IOException;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

public class HeaderAuthenticationFilter extends OncePerRequestFilter {

    public static final String HEADER_USER_ID    = "X-User-Id";
    public static final String HEADER_USERNAME   = "X-Username";
    public static final String HEADER_EMAIL      = "X-Email";
    public static final String HEADER_FIRST_NAME = "X-First-Name";
    public static final String HEADER_LAST_NAME  = "X-Last-Name";
    public static final String HEADER_ROLES      = "X-Roles";

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        String userId = request.getHeader(HEADER_USER_ID);

        if (userId != null) {
            String rolesHeader = request.getHeader(HEADER_ROLES);

            List<String> roles = rolesHeader != null && !rolesHeader.isBlank()
                    ? Arrays.stream(rolesHeader.split(","))
                            .map(String::trim)
                            .filter(r -> !r.isBlank())
                            .collect(Collectors.toList())
                    : List.of();

            List<GrantedAuthority> grantedAuthorities = roles.stream()
                    .map(SimpleGrantedAuthority::new)
                    .collect(Collectors.toList());

            UserPrincipal principal = new UserPrincipal(
                    userId,
                    request.getHeader(HEADER_USERNAME),
                    request.getHeader(HEADER_EMAIL),
                    request.getHeader(HEADER_FIRST_NAME),
                    request.getHeader(HEADER_LAST_NAME),
                    roles
            );

            SecurityContextHolder.getContext().setAuthentication(
                    new PreAuthenticatedAuthenticationToken(principal, null, grantedAuthorities)
            );
        }

        chain.doFilter(request, response);
    }
}
