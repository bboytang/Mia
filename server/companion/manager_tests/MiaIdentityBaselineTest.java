package xiaozhi.modules.device;

import static org.junit.jupiter.api.Assertions.*;

import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.Map;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

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
import xiaozhi.modules.sys.redis.SysParamsRedis;

/** Reproduces known unsafe baseline behavior on disposable CI data, NOT security acceptance. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = "server.servlet.context-path=/xiaozhi")
@ActiveProfiles("dev")
class MiaIdentityBaselineTest {
    private static final long USER_A = 910000001L;
    private static final long USER_B = 910000002L;
    private static final String AGENT_B = "mia-ci-agent-b";
    private static final String DEVICE_B = "02:00:00:00:01:02";

    @Autowired private TestRestTemplate http;
    @Autowired private JdbcTemplate db;
    @Autowired private RedisUtils redis;
    @Autowired private SysParamsRedis params;
    @Autowired private SysUserTokenService tokens;
    @Autowired private ObjectMapper mapper;

    @BeforeEach
    void fixtures() {
        db.update("DELETE FROM ai_device_address_book WHERE mac_address LIKE '02:00:00:00:01:%' OR target_mac LIKE '02:00:00:00:01:%'");
        db.update("DELETE FROM ai_device WHERE id LIKE '02:00:00:00:01:%'");
        db.update("DELETE FROM ai_agent WHERE id = ?", AGENT_B);
        db.update("DELETE FROM sys_user_token WHERE user_id IN (?,?)", USER_A, USER_B);
        db.update("DELETE FROM sys_user WHERE id IN (?,?)", USER_A, USER_B);
        for (long user : new long[]{USER_A, USER_B}) {
            db.update("INSERT INTO sys_user(id,username,super_admin,status) VALUES (?,?,0,1)",
                    user, "mia-ci-" + user);
        }
        db.update("INSERT INTO ai_agent(id,user_id,agent_name) VALUES (?,?,?)", AGENT_B, USER_B, "CI only");
        db.update("INSERT INTO ai_device(id,mac_address,user_id,agent_id,board,auto_update) VALUES (?,?,?,?,?,0)",
                DEVICE_B, DEVICE_B, USER_B, AGENT_B, "MIA_CI");
    }

    private JsonNode post(String path, Map<String, Object> body, String token) throws Exception {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        if (token != null) headers.setBearerAuth(token);
        var response = http.exchange(path, HttpMethod.POST,
                new HttpEntity<>(body, headers), String.class);
        assertNotNull(response.getBody());
        return mapper.readTree(response.getBody());
    }

    @Test
    void unsafeBaselineAnonymousOtaSignsForgedClientForBoundDevice() throws Exception {
        byte[] secret = new byte[32];
        new SecureRandom().nextBytes(secret);
        String secretText = Base64.getEncoder().encodeToString(secret);
        params.set("server.secret", secretText);
        params.set("server.auth.enabled", "true");
        params.set("server.websocket", "ws://127.0.0.1:1/xiaozhi/v1/");
        params.set("server.mqtt_gateway", "null");
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("Device-Id", DEVICE_B);
        headers.set("Client-Id", "mia-ci-forged-client");
        var response = http.exchange("/ota/", HttpMethod.POST,
                new HttpEntity<>(Map.of("application", Map.of("version", "CI")), headers), String.class);
        assertEquals(200, response.getStatusCode().value());
        String token = mapper.readTree(response.getBody()).path("websocket").path("token").asText();
        String[] parts = token.split("\\.");
        assertEquals(2, parts.length, "Unsafe baseline must issue legacy token without possession proof");
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(secretText.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        String signed = "mia-ci-forged-client|" + DEVICE_B + "|" + parts[1];
        assertEquals(Base64.getUrlEncoder().withoutPadding().encodeToString(
                mac.doFinal(signed.getBytes(StandardCharsets.UTF_8))), parts[0]);
    }

    @Test
    void unsafeBaselineAuthenticatedAAddsDeviceToBWithoutAgentPermission() throws Exception {
        Map<String, Object> body = Map.of("agentId", AGENT_B, "board", "MIA_CI",
                "appVersion", "CI", "macAddress", "02:00:00:00:01:03");
        assertNotEquals(0, post("/device/manual-add", body, null).path("code").asInt());
        String token = tokens.createToken(USER_A).getData().getToken();
        assertEquals(0, post("/device/manual-add", body, token).path("code").asInt());
        assertEquals(USER_A, db.queryForObject("SELECT user_id FROM ai_device WHERE id=?", Long.class,
                "02:00:00:00:01:03"));
        assertEquals(AGENT_B, db.queryForObject("SELECT agent_id FROM ai_device WHERE id=?", String.class,
                "02:00:00:00:01:03"));
    }

    @Test
    void unsafeBaselineAuthenticatedABindsActivationCodeToBWithoutAgentPermission() throws Exception {
        String device = "02:00:00:00:01:04";
        String code = "864201";
        redis.set(RedisKeys.getOtaActivationCode(code), device, 300);
        redis.set(RedisKeys.getOtaDeviceActivationInfo(device.replace(':', '_')),
                Map.of("mac_address", device, "activation_code", code, "board", "MIA_CI", "app_version", "CI"), 300);
        String token = tokens.createToken(USER_A).getData().getToken();
        assertEquals(0, post("/device/bind/" + AGENT_B + "/" + code, Map.of(), token).path("code").asInt());
        assertEquals(USER_A, db.queryForObject("SELECT user_id FROM ai_device WHERE id=?", Long.class, device));
        assertEquals(AGENT_B, db.queryForObject("SELECT agent_id FROM ai_device WHERE id=?", String.class, device));
    }

    @Test
    void unsafeBaselineAUnbindLeavesBDeviceButDeletesBAddressBook() throws Exception {
        db.update("INSERT INTO ai_device_address_book(mac_address,target_mac) VALUES (?,?)",
                DEVICE_B, "02:00:00:00:01:05");
        String token = tokens.createToken(USER_A).getData().getToken();
        assertEquals(0, post("/device/unbind", Map.of("deviceId", DEVICE_B), token).path("code").asInt());
        assertEquals(1, db.queryForObject("SELECT COUNT(*) FROM ai_device WHERE id=?", Integer.class, DEVICE_B));
        assertEquals(0, db.queryForObject("SELECT COUNT(*) FROM ai_device_address_book WHERE mac_address=?",
                Integer.class, DEVICE_B));
    }
}
