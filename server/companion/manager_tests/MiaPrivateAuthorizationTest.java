package xiaozhi.modules.device;

import static org.junit.jupiter.api.Assertions.*;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import xiaozhi.modules.security.service.SysUserTokenService;
import xiaozhi.modules.sys.service.SysParamsService;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = {"server.servlet.context-path=/xiaozhi", "mia.private-auth.allow-insecure-test-http=true"})
@ActiveProfiles("dev")
class MiaPrivateAuthorizationTest {
    private static final long USER_A = 930000001L;
    private static final long USER_B = 930000002L;
    private static final String AGENT_B = "mia-private-ci-b";
    private static final String DEVICE_B = "02:00:00:00:03:02";
    private static final String CLIENT = "mia-private-ci-client";
    @Autowired private TestRestTemplate http;
    @Autowired private JdbcTemplate db;
    @Autowired private StringRedisTemplate redis;
    @Autowired private SysUserTokenService tokens;
    @Autowired private SysParamsService params;
    @Autowired private ObjectMapper mapper;

    @BeforeEach
    void fixtures() {
        redis.delete(redis.keys("mia:private-auth:*"));
        db.update("DELETE FROM ai_mia_device_authorization WHERE device_id LIKE '02:00:00:00:03:%'");
        db.update("DELETE FROM ai_device WHERE id LIKE '02:00:00:00:03:%'");
        db.update("DELETE FROM ai_agent WHERE id=?", AGENT_B);
        db.update("DELETE FROM sys_user_token WHERE user_id IN (?,?)", USER_A, USER_B);
        db.update("DELETE FROM sys_user WHERE id IN (?,?)", USER_A, USER_B);
        for (long user : new long[]{USER_A, USER_B}) {
            db.update("INSERT INTO sys_user(id,username,super_admin,status) VALUES (?,?,0,1)", user, "mia-ci-" + user);
        }
        db.update("INSERT INTO ai_agent(id,user_id,agent_name) VALUES (?,?,?)", AGENT_B, USER_B, "CI only");
        db.update("INSERT INTO ai_device(id,mac_address,user_id,agent_id,board,auto_update) VALUES (?,?,?,?,?,0)",
                DEVICE_B, DEVICE_B, USER_B, AGENT_B, "MIA_CI");
    }

    private JsonNode post(String path, Map<String, Object> body, String token) throws Exception {
        return post(path, body, token, null);
    }

    private JsonNode post(String path, Map<String, Object> body, String token, String forwarded) throws Exception {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        if (token != null) headers.setBearerAuth(token);
        if (forwarded != null) headers.set("X-Forwarded-For", forwarded);
        var response = http.exchange(path, HttpMethod.POST, new HttpEntity<>(body, headers), String.class);
        assertNotNull(response.getBody());
        return mapper.readTree(response.getBody());
    }

    private String userToken(long user) {
        return tokens.createToken(user).getData().getToken();
    }

    private String code(String device, long user) throws Exception {
        JsonNode result = post("/device/mia-auth/code", Map.of("device_id", device), userToken(user));
        assertEquals(0, result.path("code").asInt());
        return result.path("data").path("authorization_code").asText();
    }

    private JsonNode exchange(String device, String client, String code) throws Exception {
        return post("/device/mia-auth/exchange", Map.of("device_id", device, "client_id", client,
                "authorization_code", code), null);
    }

    private JsonNode grant() throws Exception {
        JsonNode result = exchange(DEVICE_B, CLIENT, code(DEVICE_B, USER_B));
        assertEquals(0, result.path("code").asInt());
        return result.path("data");
    }

    private JsonNode verify(String device, String client, String credential) throws Exception {
        return post("/config/mia-auth/verify", Map.of("device_id", device, "client_id", client,
                "private_credential", credential), params.getValue("server.secret", false));
    }

    @Test
    void identifiersAndOtherUserCannotAcquirePrivateGrant() throws Exception {
        assertNotEquals(0, post("/device/mia-auth/code", Map.of("device_id", DEVICE_B), null).path("code").asInt());
        assertNotEquals(0, post("/device/mia-auth/code", Map.of("device_id", DEVICE_B), userToken(USER_A)).path("code").asInt());
        assertNotEquals(0, exchange(DEVICE_B, CLIENT, "known-device-id-is-not-proof").path("code").asInt());
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM ai_mia_device_authorization WHERE device_id=?", Integer.class, DEVICE_B));
        assertNotEquals(0, verify(DEVICE_B, CLIENT, "legacy-signature.timestamp").path("code").asInt());
    }

    @Test
    void codeIsConsumedAtomicallyAndOnlyHashesAreStored() throws Exception {
        String code = code(DEVICE_B, USER_B);
        assertTrue(code.length() >= 22);
        assertNotEquals(code, db.queryForObject("SELECT authorization_code_hash FROM ai_mia_device_authorization WHERE device_id=?", String.class, DEVICE_B));
        var pool = Executors.newFixedThreadPool(2);
        var start = new CountDownLatch(1);
        List<JsonNode> responses = new ArrayList<>();
        try {
            var first = pool.submit(() -> { start.await(); return exchange(DEVICE_B, CLIENT + "-1", code); });
            var second = pool.submit(() -> { start.await(); return exchange(DEVICE_B, CLIENT + "-2", code); });
            start.countDown();
            responses.add(first.get(15, TimeUnit.SECONDS));
            responses.add(second.get(15, TimeUnit.SECONDS));
        } finally {
            pool.shutdownNow();
        }
        assertEquals(1, responses.stream().filter(r -> r.path("code").asInt() == 0).count());
        JsonNode value = responses.stream().filter(r -> r.path("code").asInt() == 0).findFirst().orElseThrow().path("data");
        String credential = value.path("private_credential").asText();
        assertTrue(credential.length() >= 43);
        assertNull(db.queryForObject("SELECT authorization_code_hash FROM ai_mia_device_authorization WHERE device_id=?", String.class, DEVICE_B));
        String hash = db.queryForObject("SELECT credential_hash FROM ai_mia_device_authorization WHERE device_id=?", String.class, DEVICE_B);
        assertTrue(hash.matches("[a-f0-9]{64}"));
        assertNotEquals(credential, hash);
        assertEquals(0, verify(DEVICE_B, value.path("scope").path("client_id").asText(), credential).path("code").asInt());
    }

    @Test
    void expiryAndFiveFailedAttemptsAreEnforcedAndCommitted() throws Exception {
        String expired = code(DEVICE_B, USER_B);
        db.update("UPDATE ai_mia_device_authorization SET code_expires_at=UTC_TIMESTAMP()-INTERVAL 1 SECOND WHERE device_id=?", DEVICE_B);
        assertNotEquals(0, exchange(DEVICE_B, CLIENT, expired).path("code").asInt());
        String current = code(DEVICE_B, USER_B);
        for (int i = 0; i < 5; i++) assertNotEquals(0, exchange(DEVICE_B, CLIENT, "incorrect-" + i).path("code").asInt());
        assertEquals(5, db.queryForObject("SELECT wrong_attempts FROM ai_mia_device_authorization WHERE device_id=?", Integer.class, DEVICE_B));
        assertNotEquals(0, exchange(DEVICE_B, CLIENT, current).path("code").asInt());
        assertEquals(0, exchange(DEVICE_B, CLIENT, code(DEVICE_B, USER_B)).path("code").asInt());
    }

    @Test
    void scopeComesFromBindingAndRejectsDifferentDeviceClientOrExpiredCredential() throws Exception {
        JsonNode grant = grant();
        String credential = grant.path("private_credential").asText();
        JsonNode scope = grant.path("scope");
        assertEquals(USER_B, scope.path("user_id").asLong());
        assertEquals(USER_B, scope.path("operator_id").asLong());
        assertEquals("user:" + USER_B + ":agent:" + AGENT_B, scope.path("owner").asText());
        assertEquals("mia", scope.path("persona_id").asText());
        assertNotEquals(0, verify(DEVICE_B, "forged-client", credential).path("code").asInt());
        assertNotEquals(0, verify("02:00:00:00:03:99", CLIENT, credential).path("code").asInt());
        assertNotEquals(0, post("/config/mia-auth/verify", Map.of("device_id", DEVICE_B, "client_id", CLIENT,
                "private_credential", credential), userToken(USER_B)).path("code").asInt());
        db.update("UPDATE ai_mia_device_authorization SET credential_expires_at=UTC_TIMESTAMP()-INTERVAL 1 SECOND WHERE device_id=?", DEVICE_B);
        assertNotEquals(0, verify(DEVICE_B, CLIENT, credential).path("code").asInt());
        assertNotEquals(0, post("/device/mia-auth/renew", Map.of("device_id", DEVICE_B, "client_id", CLIENT,
                "private_credential", credential), null).path("code").asInt());
    }

    @Test
    void renewalRotatesAndRevocationRejectsBothTokensAndCode() throws Exception {
        JsonNode original = grant();
        String old = original.path("private_credential").asText();
        JsonNode renewed = post("/device/mia-auth/renew", Map.of("device_id", DEVICE_B, "client_id", CLIENT,
                "private_credential", old), null);
        assertEquals(0, renewed.path("code").asInt());
        String current = renewed.path("data").path("private_credential").asText();
        assertNotEquals(old, current);
        assertTrue(renewed.path("data").path("scope").path("credential_version").asLong()
                > original.path("scope").path("credential_version").asLong());
        assertNotEquals(0, verify(DEVICE_B, CLIENT, old).path("code").asInt());
        assertNotEquals(0, post("/device/mia-auth/revoke", Map.of("device_id", DEVICE_B), userToken(USER_A)).path("code").asInt());
        assertEquals(0, verify(DEVICE_B, CLIENT, current).path("code").asInt());
        String pendingCode = code(DEVICE_B, USER_B);
        assertEquals(0, post("/device/mia-auth/revoke", Map.of("device_id", DEVICE_B), userToken(USER_B)).path("code").asInt());
        assertNotEquals(0, verify(DEVICE_B, CLIENT, current).path("code").asInt());
        assertNotEquals(0, exchange(DEVICE_B, CLIENT, pendingCode).path("code").asInt());
    }

    @Test
    void unbindAndRebindSameDeviceCannotReviveOldGrant() throws Exception {
        JsonNode original = grant();
        String old = original.path("private_credential").asText();
        long version = original.path("scope").path("binding_version").asLong();
        assertEquals(0, post("/device/unbind", Map.of("deviceId", DEVICE_B), userToken(USER_B)).path("code").asInt());
        assertNotEquals(0, verify(DEVICE_B, CLIENT, old).path("code").asInt());
        assertEquals(0, post("/device/manual-add", Map.of("agentId", AGENT_B, "macAddress", DEVICE_B,
                "board", "MIA_CI", "appVersion", "CI"), userToken(USER_B)).path("code").asInt());
        JsonNode renewed = grant();
        assertEquals(DEVICE_B, renewed.path("scope").path("device_id").asText());
        assertTrue(renewed.path("scope").path("binding_version").asLong() > version);
        assertNotEquals(0, verify(DEVICE_B, CLIENT, old).path("code").asInt());
    }

    @Test
    void administratorOperatorAndDataOwnerRemainDistinctAndCurrentRoleIsChecked() throws Exception {
        String device = "02:00:00:00:03:03";
        db.update("UPDATE sys_user SET super_admin=1 WHERE id=?", USER_A);
        assertEquals(0, post("/device/manual-add", Map.of("agentId", AGENT_B, "macAddress", device,
                "board", "MIA_CI", "appVersion", "CI"), userToken(USER_A)).path("code").asInt());
        JsonNode value = exchange(device, CLIENT, code(device, USER_A)).path("data");
        String credential = value.path("private_credential").asText();
        assertEquals(USER_A, value.path("scope").path("operator_id").asLong());
        assertEquals(USER_B, value.path("scope").path("user_id").asLong());
        assertEquals(0, verify(device, CLIENT, credential).path("code").asInt());
        db.update("UPDATE sys_user SET super_admin=0 WHERE id=?", USER_A);
        assertNotEquals(0, verify(device, CLIENT, credential).path("code").asInt());
        assertNotEquals(0, post("/device/mia-auth/code", Map.of("device_id", device), userToken(USER_A)).path("code").asInt());
    }

    @Test
    void disabledOwnerOrChangedBindingFailsCurrentAuthorization() throws Exception {
        String credential = grant().path("private_credential").asText();
        db.update("UPDATE sys_user SET status=0 WHERE id=?", USER_B);
        assertNotEquals(0, verify(DEVICE_B, CLIENT, credential).path("code").asInt());
        db.update("UPDATE sys_user SET status=1 WHERE id=?", USER_B);
        db.update("UPDATE ai_device SET user_id=? WHERE id=?", USER_A, DEVICE_B);
        assertNotEquals(0, verify(DEVICE_B, CLIENT, credential).path("code").asInt());
        assertNotEquals(0, post("/device/mia-auth/code", Map.of("device_id", DEVICE_B), userToken(USER_A)).path("code").asInt());
    }

    @Test
    void forwardedHeaderCannotBypassBoundedExchangeRateLimit() throws Exception {
        long second = Instant.now().getEpochSecond() % 60;
        if (second > 55) Thread.sleep((60 - second) * 1000 + 100);
        code(DEVICE_B, USER_B);
        for (int i = 0; i < 20; i++) {
            assertNotEquals(0, post("/device/mia-auth/exchange", Map.of("device_id", DEVICE_B, "client_id", CLIENT,
                    "authorization_code", "invalid-no-grant"), null, "192.0.2." + i).path("code").asInt());
        }
        String valid = code(DEVICE_B, USER_B);
        assertNotEquals(0, post("/device/mia-auth/exchange", Map.of("device_id", DEVICE_B, "client_id", CLIENT,
                "authorization_code", valid), null, "198.51.100.1").path("code").asInt());
        assertEquals(1, redis.keys("mia:private-auth:source:*").size());
        assertEquals("21", redis.opsForValue().get(redis.keys("mia:private-auth:source:*").iterator().next()));
        assertNull(db.queryForObject("SELECT credential_hash FROM ai_mia_device_authorization WHERE device_id=?", String.class, DEVICE_B));
        assertEquals(0, db.queryForObject("SELECT wrong_attempts FROM ai_mia_device_authorization WHERE device_id=?", Integer.class, DEVICE_B));
    }
}
