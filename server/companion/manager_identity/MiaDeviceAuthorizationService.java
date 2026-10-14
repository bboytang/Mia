package xiaozhi.modules.device.service.impl;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.Base64;
import java.util.HexFormat;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

import org.springframework.context.annotation.Lazy;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import jakarta.annotation.Resource;
import lombok.RequiredArgsConstructor;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.common.user.UserDetail;
import xiaozhi.modules.agent.dao.AgentDao;
import xiaozhi.modules.agent.entity.AgentEntity;
import xiaozhi.modules.agent.service.AgentService;
import xiaozhi.modules.security.user.SecurityUser;
import xiaozhi.modules.sys.dao.SysUserDao;
import xiaozhi.modules.sys.entity.SysUserEntity;

/** Private device grants; existing manager accounts and device binding remain authoritative. */
@Service
@RequiredArgsConstructor
public class MiaDeviceAuthorizationService {
    private static final SecureRandom RANDOM = new SecureRandom();
    private static final long CREDENTIAL_SECONDS = 30L * 86400;
    private final JdbcTemplate db;
    private final AgentDao agents;
    private final SysUserDao users;
    private final RedisUtils redis;
    @Lazy @Resource private AgentService agentService;

    private record Binding(long operator, long owner, String agent) {}

    private Binding binding(String deviceId, boolean lock) {
        List<Map<String, Object>> rows = db.queryForList(
                "SELECT user_id,agent_id FROM ai_device WHERE id=?" + (lock ? " FOR UPDATE" : ""), deviceId);
        if (rows.isEmpty() || !(rows.getFirst().get("user_id") instanceof Number userId)) return null;
        if (!(rows.getFirst().get("agent_id") instanceof String agentId)) return null;
        AgentEntity agent = agents.selectById(agentId);
        if (agent == null || agent.getUserId() == null) return null;
        return new Binding(userId.longValue(), agent.getUserId(), agent.getId());
    }

    private Binding requireOwner(String deviceId) {
        Binding current = binding(deviceId, true);
        UserDetail user = SecurityUser.getUser();
        if (current == null || user == null || user.getId() == null || user.getId() != current.operator()
                || !agentService.checkAgentPermission(current.agent(), user.getId())) {
            throw new RenException(ErrorCode.NO_PERMISSION);
        }
        return current;
    }

    private void ensureRow(String deviceId) {
        db.update("INSERT IGNORE INTO ai_mia_device_authorization(device_id) VALUES (?)", deviceId);
    }

    private Map<String, Object> row(String deviceId, boolean lock) {
        List<Map<String, Object>> rows = db.query(
                "SELECT * FROM ai_mia_device_authorization WHERE device_id=?" + (lock ? " FOR UPDATE" : ""),
                (rs, index) -> {
                    Map<String, Object> result = new HashMap<>();
                    for (int column = 1; column <= rs.getMetaData().getColumnCount(); column++) {
                        result.put(rs.getMetaData().getColumnLabel(column), rs.getObject(column));
                    }
                    result.put("code_expires_at", rs.getTimestamp("code_expires_at"));
                    result.put("credential_expires_at", rs.getTimestamp("credential_expires_at"));
                    return result;
                }, deviceId);
        return rows.isEmpty() ? null : rows.getFirst();
    }

    private static long number(Map<String, Object> row, String name) {
        return ((Number) row.get(name)).longValue();
    }

    private static boolean sameBinding(Map<String, Object> row, Binding current) {
        return row != null && current != null && row.get("operator_id") instanceof Number
                && row.get("owner_id") instanceof Number
                && number(row, "operator_id") == current.operator() && number(row, "owner_id") == current.owner()
                && Objects.equals(row.get("agent_id"), current.agent());
    }

    private boolean currentAuthority(Binding current) {
        if (current == null) return false;
        SysUserEntity operator = users.selectById(current.operator());
        SysUserEntity owner = users.selectById(current.owner());
        return operator != null && owner != null && Integer.valueOf(1).equals(operator.getStatus())
                && Integer.valueOf(1).equals(owner.getStatus())
                && (current.operator() == current.owner() || Integer.valueOf(1).equals(operator.getSuperAdmin()));
    }

    private static String random(int bytes) {
        byte[] value = new byte[bytes];
        RANDOM.nextBytes(value);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(value);
    }

    private static String digest(String value) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException(impossible);
        }
    }

    private static boolean matches(Object hash, String supplied) {
        return hash instanceof String && MessageDigest.isEqual(((String) hash).getBytes(StandardCharsets.US_ASCII),
                digest(supplied).getBytes(StandardCharsets.US_ASCII));
    }

    private static boolean future(Object value) {
        return value instanceof Timestamp timestamp && timestamp.toInstant().isAfter(Instant.now());
    }

    private void rateLimit(String source) {
        long minute = Instant.now().getEpochSecond() / 60;
        // Fixed window key plus expiry keeps the global and per-source storage bounded.
        if (redis.increment("mia:private-auth:global:" + minute, 90) > 120
                || redis.increment("mia:private-auth:source:" + minute + ":" + digest(source), 90) > 20) {
            throw new RenException(ErrorCode.NO_PERMISSION);
        }
    }

    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> createCode(String deviceId) {
        Binding current = requireOwner(deviceId);
        if (!currentAuthority(current)) throw new RenException(ErrorCode.NO_PERMISSION);
        ensureRow(deviceId);
        Map<String, Object> grant = row(deviceId, true);
        if (!sameBinding(grant, current)) {
            db.update("UPDATE ai_mia_device_authorization SET credential_hash=NULL,credential_expires_at=NULL,client_id=NULL,"
                    + "revoked=1,credential_version=credential_version+1 WHERE device_id=?", deviceId);
        }
        String code = random(16);
        db.update("UPDATE ai_mia_device_authorization SET operator_id=?,owner_id=?,agent_id=?,persona_id='mia',"
                + "authorization_code_hash=?,code_expires_at=?,wrong_attempts=0 WHERE device_id=?",
                current.operator(), current.owner(), current.agent(), digest(code),
                Timestamp.from(Instant.now().plusSeconds(600)), deviceId);
        return Map.of("authorization_code", code, "expires_in", 600, "device_id", deviceId,
                "binding_version", number(grant, "binding_version"));
    }

    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> exchange(String deviceId, String clientId, String code, String source) {
        rateLimit(source);
        Binding current = binding(deviceId, true);
        Map<String, Object> grant = row(deviceId, true);
        if (!sameBinding(grant, current) || !currentAuthority(current)) return null;
        if (number(grant, "wrong_attempts") >= 5 || !future(grant.get("code_expires_at"))) return null;
        if (!matches(grant.get("authorization_code_hash"), code)) {
            db.update("UPDATE ai_mia_device_authorization SET wrong_attempts=wrong_attempts+1 WHERE device_id=?", deviceId);
            // Returning denial commits the attempt; controller raises after the transaction.
            return null;
        }
        return issue(deviceId, clientId);
    }

    private Map<String, Object> issue(String deviceId, String clientId) {
        String credential = random(32);
        db.update("UPDATE ai_mia_device_authorization SET authorization_code_hash=NULL,code_expires_at=NULL,"
                + "credential_hash=?,credential_expires_at=?,client_id=?,revoked=0,credential_version=credential_version+1 "
                + "WHERE device_id=?", digest(credential), Timestamp.from(Instant.now().plusSeconds(CREDENTIAL_SECONDS)),
                clientId, deviceId);
        Map<String, Object> grant = row(deviceId, false);
        return Map.of("private_credential", credential, "expires_in", CREDENTIAL_SECONDS, "scope", scope(grant));
    }

    private Map<String, Object> scope(Map<String, Object> grant) {
        Map<String, Object> result = new HashMap<>(Map.of("owner", "user:" + number(grant, "owner_id") + ":agent:" + grant.get("agent_id"),
                "operator_id", number(grant, "operator_id"), "user_id", number(grant, "owner_id"),
                "agent_id", grant.get("agent_id"), "persona_id", grant.get("persona_id"),
                "device_id", grant.get("device_id"), "client_id", grant.get("client_id"),
                "binding_version", number(grant, "binding_version"),
                "credential_version", number(grant, "credential_version"),
                "expires_at", ((Timestamp) grant.get("credential_expires_at")).toInstant().toString()));
        result.put("permissions", List.of("memory:read", "memory:write", "memory:manage"));
        return result;
    }

    private boolean active(Map<String, Object> grant, Binding current, String clientId) {
        Object revoked = grant == null ? null : grant.get("revoked");
        boolean isRevoked = revoked == null || Boolean.TRUE.equals(revoked)
                || (revoked instanceof Number && ((Number) revoked).intValue() != 0);
        return sameBinding(grant, current) && currentAuthority(current) && !isRevoked
                && Objects.equals(grant.get("client_id"), clientId)
                && future(grant.get("credential_expires_at")) && grant.get("credential_hash") instanceof String;
    }

    private boolean valid(Map<String, Object> grant, Binding current, String clientId, String credential) {
        return active(grant, current, clientId) && matches(grant.get("credential_hash"), credential);
    }

    @Transactional(readOnly = true)
    public Map<String, Object> verify(String deviceId, String clientId, String credential) {
        Binding current = binding(deviceId, false);
        Map<String, Object> grant = row(deviceId, false);
        return valid(grant, current, clientId, credential) ? scope(grant) : null;
    }

    @Transactional(readOnly = true)
    public Map<String, Object> checkScope(String deviceId, String clientId, String expectedOwner,
                                          long operatorId, long bindingVersion, long credentialVersion) {
        Binding current = binding(deviceId, false);
        Map<String, Object> grant = row(deviceId, false);
        if (!active(grant, current, clientId) || number(grant, "operator_id") != operatorId
                || number(grant, "binding_version") != bindingVersion
                || number(grant, "credential_version") != credentialVersion) return null;
        Map<String, Object> actual = scope(grant);
        return expectedOwner.equals(actual.get("owner")) ? actual : null;
    }

    @Transactional(rollbackFor = Exception.class)
    public Map<String, Object> renew(String deviceId, String clientId, String credential, String source) {
        rateLimit(source);
        Binding current = binding(deviceId, true);
        Map<String, Object> grant = row(deviceId, true);
        return valid(grant, current, clientId, credential) ? issue(deviceId, clientId) : null;
    }

    @Transactional(rollbackFor = Exception.class)
    public void revoke(String deviceId) {
        requireOwner(deviceId);
        ensureRow(deviceId);
        invalidate("device_id=?", deviceId, false);
    }

    private void invalidate(String condition, Object value, boolean bindingChange) {
        // Conditions are fixed internal call sites, never network input.
        db.update("UPDATE ai_mia_device_authorization SET revoked=1,authorization_code_hash=NULL,code_expires_at=NULL,"
                + "credential_hash=NULL,credential_expires_at=NULL,client_id=NULL,credential_version=credential_version+1"
                + (bindingChange ? ",binding_version=binding_version+1" : "") + " WHERE " + condition, value);
    }

    @Transactional(rollbackFor = Exception.class)
    public void bindingChanged(String deviceId) {
        ensureRow(deviceId);
        invalidate("device_id=?", deviceId, true);
    }

    @Transactional(rollbackFor = Exception.class)
    public void agentDeleted(String agentId) {
        invalidate("agent_id=?", agentId, true);
    }

    @Transactional(rollbackFor = Exception.class)
    public void userDeleted(Long userId) {
        invalidate("operator_id=?", userId, true);
        invalidate("owner_id=?", userId, true);
    }
}
