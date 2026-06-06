package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.client.yougile.api.DefaultApi;
import ru.team42.monolith.client.yougile.model.CredentialsWithCompanyDto;
import ru.team42.monolith.client.yougile.model.CredentialsWithNameDto;
import ru.team42.monolith.config.YougileClientConfig;
import ru.team42.monolith.dto.request.CreateInviteRequest;
import ru.team42.monolith.dto.request.CreateUserRequest;
import ru.team42.monolith.dto.request.LoginRequest;
import ru.team42.monolith.dto.request.TelegramOAuthRequest;
import ru.team42.monolith.dto.request.UpdateTeamRequest;
import ru.team42.monolith.dto.request.YouGileAuthRequest;
import ru.team42.monolith.dto.request.YouGileBoardSelectRequest;
import ru.team42.monolith.dto.request.YouGileConnectRequest;
import ru.team42.monolith.dto.request.YouGileCredentialsRequest;
import ru.team42.monolith.dto.response.AuthResponse;
import ru.team42.monolith.dto.response.InviteResponse;
import ru.team42.monolith.dto.response.TeamResponse;
import ru.team42.monolith.dto.response.TelegramAuthResponse;
import ru.team42.monolith.dto.response.YouGileAuthResponse;
import ru.team42.monolith.dto.response.YouGileBoardResponse;
import ru.team42.monolith.dto.response.YouGileCompanyResponse;
import ru.team42.monolith.dto.response.YouGileProjectResponse;
import ru.team42.monolith.entity.Team;
import ru.team42.monolith.entity.TeamUser;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.entity.YouGileCompany;
import ru.team42.monolith.entity.enums.TeamRole;
import ru.team42.monolith.repository.TeamRepository;
import ru.team42.monolith.repository.TeamUserRepository;
import ru.team42.monolith.repository.UserRepository;
import ru.team42.monolith.repository.YouGileCompanyRepository;
import ru.team42.monolith.security.JwtService;
import ru.team42.monolith.security.TelegramOAuthVerifier;

import java.util.List;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuthService {

    private final TeamRepository teamRepository;
    private final TeamUserRepository teamUserRepository;
    private final UserRepository userRepository;
    private final YouGileCompanyRepository youGileCompanyRepository;
    private final TeamService teamService;
    private final DefaultApi yougileUnauthenticatedApi;
    private final TelegramOAuthVerifier telegramOAuthVerifier;
    private final JwtService jwtService;

    @Transactional(readOnly = true)
    public InviteResponse createInvite(CreateInviteRequest request) {
        Team team = teamRepository.findByTelegramChatIdAndActiveTrue(request.chatId())
                .orElseThrow(() -> AppException.notFound("Team for chatId %d not found".formatted(request.chatId())));
        return new InviteResponse(team.getId());
    }

    @Transactional
    public AuthResponse joinTeam(UUID teamId, LoginRequest request) {
        Team team = teamRepository.findById(teamId)
                .orElseThrow(() -> AppException.notFound("Team %s not found".formatted(teamId)));

        User user = userRepository.findByTelegramId(request.telegramId())
                .orElseGet(() -> createUser(request));

        boolean alreadyMember = teamUserRepository.findByTeamIdAndUserId(teamId, user.getId()).isPresent();

        if (!alreadyMember) {
            TeamUser teamUser = new TeamUser();
            teamUser.setTeam(team);
            teamUser.setUser(user);
            teamUser.setRole(TeamRole.USER);
            teamUser.setPosition(request.position());

            if (request.yougileLogin() != null && request.yougilePassword() != null && team.getCompany() != null) {
                try {
                    String apiKey = fetchApiKey(request.yougileLogin(), request.yougilePassword(),
                            team.getCompany().getYougileCompanyId());
                    var api = YougileClientConfig.createAuthenticatedApi(apiKey);
                    var yougileUser = api.userControllerGetMe().block();
                    if (yougileUser != null && yougileUser.getId() != null) {
                        teamUser.setYougileUserApiKey(apiKey);
                        teamUser.setYougileUserId(yougileUser.getId());
                    }
                } catch (Exception e) {
                    log.warn("Failed to fetch YouGile user for team {}: {}", teamId, e.getMessage());
                }
            }

            teamUserRepository.save(teamUser);
        }

        return new AuthResponse(user.getId(), user.getTelegramId(), user.getSystemRole());
    }

    public List<YouGileCompanyResponse> listYouGileCompanies(YouGileCredentialsRequest request) {
        var creds = new CredentialsWithNameDto();
        creds.setLogin(request.login());
        creds.setPassword(request.password());
        try {
            var result = yougileUnauthenticatedApi.getCompanies(creds, null, null).block();
            if (result == null) return List.of();
            return result.getContent().stream()
                    .map(c -> new YouGileCompanyResponse(c.getId(), c.getName(), c.getIsAdmin()))
                    .toList();
        } catch (Exception e) {
            log.error("Failed to list YouGile companies: {}", e.getMessage());
            throw AppException.internalError("YouGile API unavailable: " + e.getMessage());
        }
    }

    @Transactional
    public TeamResponse connectYouGile(YouGileConnectRequest request) {
        var creds = new CredentialsWithCompanyDto();
        creds.setLogin(request.login());
        creds.setPassword(request.password());
        creds.setCompanyId(request.companyId());
        try {
            var keyDto = yougileUnauthenticatedApi.authKeyControllerCreate(creds).block();
            if (keyDto == null || keyDto.getKey() == null) {
                throw AppException.internalError("YouGile returned no API key");
            }
            return teamService.update(request.teamId(),
                    new UpdateTeamRequest(null, null, null, keyDto.getKey()));
        } catch (AppException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to get YouGile API key: {}", e.getMessage());
            throw AppException.internalError("YouGile API unavailable: " + e.getMessage());
        }
    }

    public List<YouGileProjectResponse> listYouGileProjects(UUID teamId) {
        var api = authenticatedApi(teamId);
        try {
            var result = api.projectControllerSearch(false, null, null, null).block();
            if (result == null) return List.of();
            return result.getContent().stream()
                    .map(p -> new YouGileProjectResponse(p.getId(), p.getTitle()))
                    .toList();
        } catch (AppException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to list YouGile projects for team {}: {}", teamId, e.getMessage());
            throw AppException.internalError("YouGile API unavailable: " + e.getMessage());
        }
    }

    public List<YouGileBoardResponse> listYouGileBoards(UUID teamId, String projectId) {
        var api = authenticatedApi(teamId);
        try {
            var result = api.boardControllerSearch(false, null, null, null, projectId).block();
            if (result == null) return List.of();
            return result.getContent().stream()
                    .map(b -> new YouGileBoardResponse(b.getId(), b.getTitle(), b.getProjectId()))
                    .toList();
        } catch (AppException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to list YouGile boards for team {}: {}", teamId, e.getMessage());
            throw AppException.internalError("YouGile API unavailable: " + e.getMessage());
        }
    }

    @Transactional
    public YouGileAuthResponse yougileAuth(YouGileAuthRequest request, Long managerTelegramId) {
        var companies = fetchCompanies(request.login(), request.password());

        String companyId = request.companyId();
        if (companyId == null && companies.size() == 1) {
            companyId = companies.get(0).id();
        }

        if (companyId == null) {
            return new YouGileAuthResponse(false, companies, null);
        }

        String apiKey = fetchApiKey(request.login(), request.password(), companyId);
        Team team = teamRepository.findByTelegramChatIdAndActiveTrue(request.chatId())
                .orElseThrow(() -> AppException.notFound("Team for chatId %d not found".formatted(request.chatId())));
        team.setKanbanApiKey(apiKey);

        final String resolvedCompanyId = companyId;
        YouGileCompany companyEntity = new YouGileCompany();
        companyEntity.setYougileCompanyId(resolvedCompanyId);
        companies.stream()
                .filter(c -> resolvedCompanyId.equals(c.id()))
                .findFirst()
                .ifPresent(c -> companyEntity.setName(c.name()));
        team.setCompany(youGileCompanyRepository.save(companyEntity));

        teamRepository.save(team);

        if (managerTelegramId != null) {
            try {
                var api = YougileClientConfig.createAuthenticatedApi(apiKey);
                var yougileUser = api.userControllerGetMe().block();
                if (yougileUser != null && yougileUser.getId() != null) {
                    final String yougileUserId = yougileUser.getId();
                    teamUserRepository.findByTeamIdAndUserTelegramId(team.getId(), managerTelegramId)
                            .ifPresent(tu -> {
                                tu.setYougileUserId(yougileUserId);
                                teamUserRepository.save(tu);
                            });
                }
            } catch (Exception e) {
                log.warn("Failed to set YouGile user ID for manager {}: {}", managerTelegramId, e.getMessage());
            }
        }

        var boards = fetchBoards(apiKey);
        return new YouGileAuthResponse(true, null, boards);
    }

    @Transactional
    public TeamResponse yougileSelectBoard(YouGileBoardSelectRequest request) {
        Team team = teamRepository.findByTelegramChatIdAndActiveTrue(request.chatId())
                .orElseThrow(() -> AppException.notFound("Team for chatId %d not found".formatted(request.chatId())));
        return teamService.update(team.getId(), new UpdateTeamRequest(null, null, request.boardId(), null));
    }

    private List<YouGileCompanyResponse> fetchCompanies(String login, String password) {
        var creds = new CredentialsWithNameDto();
        creds.setLogin(login);
        creds.setPassword(password);
        try {
            var result = yougileUnauthenticatedApi.getCompanies(creds, null, null).block();
            if (result == null) return List.of();
            return result.getContent().stream()
                    .map(c -> new YouGileCompanyResponse(c.getId(), c.getName(), c.getIsAdmin()))
                    .toList();
        } catch (Exception e) {
            log.error("Failed to list YouGile companies: {}", e.getMessage());
            throw AppException.internalError("YouGile API unavailable: " + e.getMessage());
        }
    }

    private String fetchApiKey(String login, String password, String companyId) {
        var creds = new CredentialsWithCompanyDto();
        creds.setLogin(login);
        creds.setPassword(password);
        creds.setCompanyId(companyId);
        try {
            var keyDto = yougileUnauthenticatedApi.authKeyControllerCreate(creds).block();
            if (keyDto == null || keyDto.getKey() == null) {
                throw AppException.internalError("YouGile returned no API key");
            }
            return keyDto.getKey();
        } catch (AppException e) {
            throw e;
        } catch (Exception e) {
            log.error("Failed to get YouGile API key: {}", e.getMessage());
            throw AppException.internalError("YouGile API unavailable: " + e.getMessage());
        }
    }

    private List<YouGileBoardResponse> fetchBoards(String apiKey) {
        var api = YougileClientConfig.createAuthenticatedApi(apiKey);
        try {
            var result = api.boardControllerSearch(false, null, null, null, null).block();
            if (result == null) return List.of();
            return result.getContent().stream()
                    .map(b -> new YouGileBoardResponse(b.getId(), b.getTitle(), b.getProjectId()))
                    .toList();
        } catch (Exception e) {
            log.warn("Failed to fetch boards: {}", e.getMessage());
            return List.of();
        }
    }

    private DefaultApi authenticatedApi(UUID teamId) {
        Team team = teamRepository.findById(teamId)
                .orElseThrow(() -> AppException.notFound("Team %s not found".formatted(teamId)));
        if (team.getKanbanApiKey() == null) {
            throw AppException.badRequest("Team %s has no YouGile API key — run /auth/yougile/connect first".formatted(teamId));
        }
        return YougileClientConfig.createAuthenticatedApi(team.getKanbanApiKey());
    }

    @Transactional
    public TelegramAuthResponse telegramOAuth(TelegramOAuthRequest request) {
        if (!telegramOAuthVerifier.verify(request)) {
            throw AppException.unauthorized("Telegram OAuth signature invalid or expired");
        }
        User user = userRepository.findByTelegramId(request.id())
                .orElseGet(User::new);
        user.setTelegramId(request.id());
        if (request.username() != null) user.setTelegramLogin(request.username());
        if (request.firstName() != null) user.setFirstName(request.firstName());
        if (request.lastName() != null) user.setLastName(request.lastName());
        user = userRepository.save(user);
        String token = jwtService.generateToken(user);
        return new TelegramAuthResponse(user.getId(), user.getTelegramId(), user.getSystemRole(), token);
    }

    @Transactional
    public AuthResponse registerUser(CreateUserRequest request) {
        User user = userRepository.findByTelegramId(request.telegramId())
                .orElseGet(User::new);
        user.setTelegramId(request.telegramId());
        user.setTelegramLogin(request.telegramLogin());
        user.setFirstName(request.firstName());
        user.setLastName(request.lastName());
        user = userRepository.save(user);
        return new AuthResponse(user.getId(), user.getTelegramId(), user.getSystemRole());
    }

    private User createUser(LoginRequest request) {
        User user = new User();
        user.setTelegramId(request.telegramId());
        user.setTelegramLogin(request.telegramLogin());
        user.setFirstName(request.firstName());
        user.setLastName(request.lastName());
        return userRepository.save(user);
    }
}
