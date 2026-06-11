package ru.team42.monolith.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import ru.team42.backend.web_common.exception.AppException;
import ru.team42.monolith.client.yougile.api.DefaultApi;
import ru.team42.monolith.client.yougile.model.CredentialsWithCompanyDto;
import ru.team42.monolith.client.yougile.model.CredentialsWithNameDto;
import ru.team42.monolith.config.YougileClientConfig;
import ru.team42.monolith.dto.request.CreateInviteRequest;
import ru.team42.monolith.dto.request.CreateUserRequest;
import ru.team42.monolith.dto.request.ConfirmExtensionLoginRequest;
import ru.team42.monolith.dto.request.LoginRequest;
import ru.team42.monolith.dto.request.UpdateYouGileProfileRequest;
import ru.team42.monolith.dto.request.TelegramOAuthRequest;
import ru.team42.monolith.dto.request.UpdateTeamRequest;
import ru.team42.monolith.dto.request.YouGileAuthRequest;
import ru.team42.monolith.dto.request.YouGileBoardSelectRequest;
import ru.team42.monolith.dto.request.YouGileConnectRequest;
import ru.team42.monolith.dto.request.YouGileCredentialsRequest;
import ru.team42.monolith.dto.response.AuthResponse;
import ru.team42.monolith.dto.response.ExtensionLoginStartResponse;
import ru.team42.monolith.dto.response.ExtensionLoginStatusResponse;
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
import ru.team42.monolith.security.TelegramInitDataVerifier;
import ru.team42.monolith.security.TelegramOAuthVerifier;

import java.util.List;
import java.security.SecureRandom;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuthService {

    private static final String YOUGILE_INVALID_CREDENTIALS_DETAIL =
            "Не удалось войти в YouGile: проверьте логин и пароль.";

    private final TeamRepository teamRepository;
    private final TeamUserRepository teamUserRepository;
    private final UserRepository userRepository;
    private final YouGileCompanyRepository youGileCompanyRepository;
    private final TeamService teamService;
    private final DefaultApi yougileUnauthenticatedApi;
    private final TelegramOAuthVerifier telegramOAuthVerifier;
    private final TelegramInitDataVerifier telegramInitDataVerifier;
    private final JwtService jwtService;
    private final Map<String, ExtensionLoginSession> extensionLoginSessions = new ConcurrentHashMap<>();
    private final SecureRandom secureRandom = new SecureRandom();

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
                    log.info("Fetched YouGile API key for user {} in team {}: {}", user.getTelegramId(), teamId, apiKey);
                    var yougileUser = api.userControllerGetMe().block();
                    if (yougileUser != null) {
                        log.info("Fetched YouGile user for user {} in team {}: YouGile user ID {}", user.getTelegramId(), teamId, yougileUser.getId());
                        teamUser.setYougileUserApiKey(apiKey);
                        teamUser.setYougileUserId(yougileUser.getId());
                    }
                    log.info("Finished YouGile auth for user {} in team {}", user.getTelegramId(), teamId);
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
        } catch (WebClientResponseException e) {
            throw youGileAuthFailure("listing companies", e);
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
        } catch (WebClientResponseException e) {
            throw youGileAuthFailure("getting API key", e);
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
                log.info("Try connect YouGile user for manager {} in team {}: API key {}, YouGile user {}",
                        managerTelegramId, team.getId(), apiKey, yougileUser != null ? yougileUser.getId() : "null");
                if (yougileUser != null) {
                    final String yougileUserId = yougileUser.getId();
                    log.info("Fetched YouGile user for manager {} in team {}: YouGile user ID {}", managerTelegramId, team.getId(), yougileUserId);
                    teamUserRepository.findByTeamIdAndUserTelegramId(team.getId(), managerTelegramId)
                            .ifPresent(tu -> {
                                tu.setYougileUserId(yougileUserId);
                                tu.setYougileUserApiKey(apiKey);
                                teamUserRepository.save(tu);
                                log.info("Updated TeamUser for manager {} + {}: set YouGile user ID {} and API key",
                                        managerTelegramId, tu, yougileUserId);
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
        } catch (WebClientResponseException e) {
            throw youGileAuthFailure("listing companies", e);
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
        } catch (WebClientResponseException e) {
            throw youGileAuthFailure("getting API key", e);
        } catch (Exception e) {
            log.error("Failed to get YouGile API key: {}", e.getMessage());
            throw AppException.internalError("YouGile API unavailable: " + e.getMessage());
        }
    }

    private AppException youGileAuthFailure(String operation, WebClientResponseException e) {
        int status = e.getStatusCode().value();
        if (status == 401) {
            log.warn("YouGile rejected credentials while {}: status={}", operation, status);
            return AppException.unauthorized(YOUGILE_INVALID_CREDENTIALS_DETAIL);
        }

        log.error("YouGile API failed while {}: status={} message={}", operation, status, e.getMessage());
        return AppException.internalError("YouGile API unavailable: " + status + " " + e.getStatusText());
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

    public ExtensionLoginStartResponse createExtensionLogin() {
        cleanupExpiredExtensionLogins();

        String code;
        do {
            code = "%06d".formatted(secureRandom.nextInt(1_000_000));
        } while (extensionLoginSessions.containsKey(code));

        Instant expiresAt = Instant.now().plus(5, ChronoUnit.MINUTES);
        extensionLoginSessions.put(code, new ExtensionLoginSession(code, expiresAt, null));
        return new ExtensionLoginStartResponse(code, expiresAt);
    }

    public ExtensionLoginStatusResponse getExtensionLogin(String code) {
        var session = extensionLoginSessions.get(normalizeCode(code));
        if (session == null) {
            return new ExtensionLoginStatusResponse("expired", normalizeCode(code), Instant.now(), null);
        }
        if (session.isExpired()) {
            extensionLoginSessions.remove(session.code());
            return new ExtensionLoginStatusResponse("expired", session.code(), session.expiresAt(), null);
        }
        if (session.auth() != null) {
            return new ExtensionLoginStatusResponse("confirmed", session.code(), session.expiresAt(), session.auth());
        }
        return new ExtensionLoginStatusResponse("pending", session.code(), session.expiresAt(), null);
    }

    @Transactional
    public ExtensionLoginStatusResponse confirmExtensionLogin(String code, ConfirmExtensionLoginRequest request) {
        String normalizedCode = normalizeCode(code);
        var session = extensionLoginSessions.get(normalizedCode);
        if (session == null || session.isExpired()) {
            extensionLoginSessions.remove(normalizedCode);
            throw AppException.notFound("Extension login code expired or not found");
        }

        User user = userRepository.findByTelegramId(request.telegramId())
                .orElseGet(User::new);
        user.setTelegramId(request.telegramId());
        if (request.telegramLogin() != null) user.setTelegramLogin(request.telegramLogin());
        if (request.firstName() != null) user.setFirstName(request.firstName());
        if (request.lastName() != null) user.setLastName(request.lastName());
        user = userRepository.save(user);

        var auth = new TelegramAuthResponse(
                user.getId(),
                user.getTelegramId(),
                user.getSystemRole(),
                jwtService.generateToken(user)
        );
        var confirmed = new ExtensionLoginSession(session.code(), session.expiresAt(), auth);
        extensionLoginSessions.put(session.code(), confirmed);
        return new ExtensionLoginStatusResponse("confirmed", session.code(), session.expiresAt(), auth);
    }

    @Transactional
    public void updateYouGileProfile(UUID teamId, UpdateYouGileProfileRequest request) {
        Team team = teamRepository.findById(teamId)
                .orElseThrow(() -> AppException.notFound("Team %s not found".formatted(teamId)));

        TeamUser teamUser = teamUserRepository.findByTeamIdAndUserTelegramId(teamId, request.telegramId())
                .orElseThrow(() -> AppException.notFound(
                        "User %d is not a member of team %s".formatted(request.telegramId(), teamId)));

        if (team.getCompany() == null) {
            throw AppException.badRequest("Team %s has no YouGile company configured".formatted(teamId));
        }

        String apiKey = fetchApiKey(request.yougileLogin(), request.yougilePassword(),
                team.getCompany().getYougileCompanyId());

        String yougileUserId = null;
        try {
            var api = YougileClientConfig.createAuthenticatedApi(apiKey);
            var yougileUser = api.userControllerGetMe().block();
            if (yougileUser != null) {
                yougileUserId = yougileUser.getId();
            }
        } catch (Exception e) {
            log.warn("Failed to fetch YouGile user profile for user {} in team {}: {}",
                    request.telegramId(), teamId, e.getMessage());
        }

        teamUser.setYougileUserApiKey(apiKey);
        if (yougileUserId != null) {
            teamUser.setYougileUserId(yougileUserId);
        }
        teamUserRepository.save(teamUser);
        log.info("Updated YouGile profile for user {} in team {}: YouGile user ID {}",
                request.telegramId(), teamId, yougileUserId);
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

    @Transactional
    public TelegramAuthResponse loginWithMiniApp(String initData) {
        if (initData == null || initData.isBlank()) {
            throw AppException.unauthorized("X-Telegram-Init-Data header is missing");
        }
        if (!telegramInitDataVerifier.verify(initData)) {
            throw AppException.unauthorized("Telegram Mini App initData signature invalid");
        }
        TelegramInitDataVerifier.TelegramUserInfo info = telegramInitDataVerifier.extractUserInfo(initData)
                .orElseThrow(() -> AppException.badRequest("Cannot extract user from initData"));

        User user = userRepository.findByTelegramId(info.id()).orElseGet(User::new);
        user.setTelegramId(info.id());
        if (info.firstName() != null) user.setFirstName(info.firstName());
        if (info.lastName() != null) user.setLastName(info.lastName());
        if (info.username() != null) user.setTelegramLogin(info.username());
        user = userRepository.save(user);

        String token = jwtService.generateToken(user);
        return new TelegramAuthResponse(user.getId(), user.getTelegramId(), user.getSystemRole(), token);
    }

    private User createUser(LoginRequest request) {
        User user = new User();
        user.setTelegramId(request.telegramId());
        user.setTelegramLogin(request.telegramLogin());
        user.setFirstName(request.firstName());
        user.setLastName(request.lastName());
        return userRepository.save(user);
    }

    private String normalizeCode(String code) {
        return code == null ? "" : code.trim();
    }

    private void cleanupExpiredExtensionLogins() {
        extensionLoginSessions.entrySet().removeIf(entry -> entry.getValue().isExpired());
    }

    private record ExtensionLoginSession(
            String code,
            Instant expiresAt,
            TelegramAuthResponse auth
    ) {
        boolean isExpired() {
            return Instant.now().isAfter(expiresAt);
        }
    }
}
