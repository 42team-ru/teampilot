package ru.team42.backend.security_common.model;

import java.security.Principal;
import java.util.List;

public record UserPrincipal(String userId, String username, String email, String firstName, String lastName,
                            List<String> roles) implements Principal
{

    @Override
    public String getName()
    {
        return username;
    }
}
