package xiaozhi.modules.device;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Map;
import java.util.concurrent.TimeUnit;
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
import xiaozhi.modules.security.service.SysUserTokenService;
import xiaozhi.modules.sys.service.SysParamsService;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
    "server.servlet.context-path=/youmi", "server.ssl.enabled=true",
    "server.ssl.key-store=${MIA_SCOPE_KEYSTORE}", "server.ssl.key-store-password=youmi-ci-only",
    "server.ssl.key-store-type=PKCS12", "mia.private-auth.allow-insecure-test-http=false"
})
@ActiveProfiles("dev")
class YoumiPrivateTlsTest {
    @Autowired private TestRestTemplate http;
    @Autowired private JdbcTemplate db;
    @Autowired private SysUserTokenService tokens;
    @Autowired private SysParamsService params;
    @Autowired private ObjectMapper mapper;

    private String base() {
        return http.getRootUri().replaceFirst("^http:", "https:").replace("localhost", "127.0.0.1");
    }

    private JsonNode post(String path, Map<String, Object> body, String token) throws Exception {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        if (token != null) headers.setBearerAuth(token);
        var response = http.exchange(java.net.URI.create(base() + path), HttpMethod.POST,
                new HttpEntity<>(body, headers), String.class);
        return mapper.readTree(response.getBody());
    }

    @Test
    void actualHttpsGrantAndVerifiedWssRejectLegacyOnlyAndStopAfterRevocation() throws Exception {
        long user = 930010001L;
        String agent = "mia-tls-ci", device = "02:00:00:00:04:01", client = "mia-tls-client";
        db.update("DELETE FROM ai_mia_device_authorization WHERE device_id=?", device);
        db.update("DELETE FROM ai_device WHERE id=?", device);
        db.update("DELETE FROM ai_agent WHERE id=?", agent);
        db.update("DELETE FROM sys_user_token WHERE user_id=?", user);
        db.update("DELETE FROM sys_user WHERE id=?", user);
        db.update("INSERT INTO sys_user(id,username,super_admin,status) VALUES (?,?,0,1)", user, "mia-tls-ci");
        db.update("INSERT INTO ai_agent(id,user_id,agent_name,system_prompt) VALUES (?,?,?,?)",
                agent, user, "CI only", "CI private prompt marker");
        db.update("INSERT INTO ai_device(id,mac_address,user_id,agent_id,board,auto_update) VALUES (?,?,?,?,?,0)",
                device, device, user, agent, "MIA_CI");
        db.update("UPDATE ai_agent SET llm_model_id=? WHERE id=?", "LLM_ChatGLMLLM", agent);
        String token = tokens.createToken(user).getData().getToken();
        JsonNode code = post("/device/mia-auth/code", Map.of("device_id", device), token);
        assertEquals(0, code.path("code").asInt());
        JsonNode grant = post("/device/mia-auth/exchange", Map.of("device_id", device, "client_id", client,
                "authorization_code", code.path("data").path("authorization_code").asText()), null);
        assertEquals(0, grant.path("code").asInt());
        ProcessBuilder process = new ProcessBuilder("python", System.getenv("MIA_SCOPE_INTEGRATION_SCRIPT")).redirectErrorStream(true);
        var env = process.environment();
        env.put("MIA_SCOPE_MANAGER_URL", base() + "/");
        env.put("MIA_SCOPE_SERVER_SECRET", params.getValue("server.secret", false));
        env.put("MIA_SCOPE_DEVICE", device);
        env.put("MIA_SCOPE_CLIENT", client);
        env.put("MIA_SCOPE_CREDENTIAL", grant.path("data").path("private_credential").asText());
        env.put("MIA_SCOPE_USER_TOKEN", token);
        env.put("MIA_SCOPE_NATIVE_TLS", "true");
        Process running = process.start();
        if (!running.waitFor(30, TimeUnit.SECONDS)) { running.destroyForcibly(); fail("Actual TLS Scope test timed out"); }
        String output = new String(running.getInputStream().readAllBytes(), java.nio.charset.StandardCharsets.UTF_8);
        assertEquals(0, running.exitValue(), output);
        assertTrue(output.contains("\"manager_python_scope_pass\": true"), output);
        assertTrue(output.contains("\"native_wss_scope_pass\": true"), output);
    }
}
