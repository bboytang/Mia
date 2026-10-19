package xiaozhi.modules.device;

import static org.junit.jupiter.api.Assertions.*;

import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import xiaozhi.common.redis.RedisKeys;
import xiaozhi.common.redis.RedisUtils;
import xiaozhi.modules.security.service.SysUserTokenService;

/** Real HTTP and persisted identities; no mocked authentication or authorization. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = "server.servlet.context-path=/youmi")
@ActiveProfiles("dev")
class YoumiBindingAuthorizationTest {
    private static final long USER_A = 920000001L;
    private static final long USER_B = 920000002L;
    private static final String AGENT_B = "mia-binding-ci-b";
    private static final String DEVICE_B = "02:00:00:00:02:02";

    @Autowired private TestRestTemplate http;
    @Autowired private JdbcTemplate db;
    @Autowired private RedisUtils redis;
    @Autowired private SysUserTokenService tokens;
    @Autowired private ObjectMapper mapper;

    @BeforeEach
    void fixtures() {
        db.update("DELETE FROM ai_device_address_book WHERE mac_address LIKE '02:00:00:00:02:%' OR target_mac LIKE '02:00:00:00:02:%'");
        db.update("DELETE FROM ai_device WHERE id LIKE '02:00:00:00:02:%'");
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
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        if (token != null) headers.setBearerAuth(token);
        var response = http.exchange(path, HttpMethod.POST, new HttpEntity<>(body, headers), String.class);
        assertNotNull(response.getBody());
        return mapper.readTree(response.getBody());
    }

    @Test
    void manualAddRejectsAnonymousOtherOwnerAndExpiredTokenAllowsOwner() throws Exception {
        String device = "02:00:00:00:02:03";
        Map<String, Object> body = Map.of("agentId", AGENT_B, "board", "MIA_CI", "appVersion", "CI", "macAddress", device);
        assertNotEquals(0, post("/device/manual-add", body, null).path("code").asInt());
        assertNotEquals(0, post("/device/manual-add", body, tokens.createToken(USER_A).getData().getToken()).path("code").asInt());
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM ai_device WHERE id=?", Integer.class, device));
        String token = tokens.createToken(USER_B).getData().getToken();
        tokens.logout(USER_B);
        assertNotEquals(0, post("/device/manual-add", body, token).path("code").asInt());
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM ai_device WHERE id=?", Integer.class, device));
        token = tokens.createToken(USER_B).getData().getToken();
        assertEquals(0, post("/device/manual-add", body, token).path("code").asInt());
        assertEquals(USER_B, db.queryForObject("SELECT user_id FROM ai_device WHERE id=?", Long.class, device));
        assertEquals(AGENT_B, db.queryForObject("SELECT agent_id FROM ai_device WHERE id=?", String.class, device));
    }

    @Test
    void activationRejectsOtherOwnerBeforeConsumptionAllowsOwner() throws Exception {
        String device = "02:00:00:00:02:04";
        String code = "864202";
        String codeKey = RedisKeys.getOtaActivationCode(code);
        String dataKey = RedisKeys.getOtaDeviceActivationInfo(device.replace(':', '_'));
        redis.set(codeKey, device, 300);
        redis.set(dataKey, new HashMap<>(Map.of("mac_address", device, "activation_code", code,
                "board", "MIA_CI", "app_version", "CI")), 300);
        String path = "/device/bind/" + AGENT_B + "/" + code;
        assertNotEquals(0, post(path, Map.of(), tokens.createToken(USER_A).getData().getToken()).path("code").asInt());
        assertEquals(device, redis.get(codeKey));
        assertNotNull(redis.get(dataKey));
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM ai_device WHERE id=?", Integer.class, device));
        assertEquals(0, post(path, Map.of(), tokens.createToken(USER_B).getData().getToken()).path("code").asInt());
        assertEquals(USER_B, db.queryForObject("SELECT user_id FROM ai_device WHERE id=?", Long.class, device));
        assertNull(redis.get(codeKey));
        assertNull(redis.get(dataKey));
    }

    @Test
    void unbindRejectsOtherOwnerWithoutSideEffectsAllowsOwner() throws Exception {
        db.update("INSERT INTO ai_device_address_book(mac_address,target_mac) VALUES (?,?),(?,?)",
                DEVICE_B, "02:00:00:00:02:05", "02:00:00:00:02:05", DEVICE_B);
        Map<String, Object> body = Map.of("deviceId", DEVICE_B);
        assertNotEquals(0, post("/device/unbind", body, tokens.createToken(USER_A).getData().getToken()).path("code").asInt());
        assertEquals(1, db.queryForObject("SELECT COUNT(*) FROM ai_device WHERE id=?", Integer.class, DEVICE_B));
        assertEquals(2, db.queryForObject("SELECT COUNT(*) FROM ai_device_address_book WHERE mac_address=? OR target_mac=?",
                Integer.class, DEVICE_B, DEVICE_B));
        assertEquals(0, post("/device/unbind", body, tokens.createToken(USER_B).getData().getToken()).path("code").asInt());
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM ai_device WHERE id=?", Integer.class, DEVICE_B));
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM ai_device_address_book WHERE mac_address=? OR target_mac=?",
                Integer.class, DEVICE_B, DEVICE_B));
    }

    @Test
    void existingAdministratorAgentPermissionIsPreserved() throws Exception {
        db.update("UPDATE sys_user SET super_admin=1 WHERE id=?", USER_A);
        String device = "02:00:00:00:02:06";
        var body = Map.<String, Object>of("agentId", AGENT_B, "board", "MIA_CI", "appVersion", "CI", "macAddress", device);
        assertEquals(0, post("/device/manual-add", body, tokens.createToken(USER_A).getData().getToken()).path("code").asInt());
        assertEquals(USER_A, db.queryForObject("SELECT user_id FROM ai_device WHERE id=?", Long.class, device));
        assertEquals(AGENT_B, db.queryForObject("SELECT agent_id FROM ai_device WHERE id=?", String.class, device));
    }
}
