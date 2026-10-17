package xiaozhi.modules.device;

import static org.junit.jupiter.api.Assertions.*;

import java.io.File;
import java.net.URI;
import java.util.ArrayList;
import java.util.List;
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

/** P23 shared-envelope preflight; no Provider or P22 semantic acceptance cases. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT, properties = {
    "server.servlet.context-path=/xiaozhi", "server.ssl.enabled=true",
    "server.ssl.key-store=${MIA_SCOPE_KEYSTORE}", "server.ssl.key-store-password=mia-ci-only",
    "server.ssl.key-store-type=PKCS12", "mia.private-auth.allow-insecure-test-http=false",
    "logging.level.root=ERROR"
})
@ActiveProfiles("dev")
class MiaPerformanceIntegrationTest {
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
        return mapper.readTree(http.exchange(URI.create(base() + path), HttpMethod.POST,
            new HttpEntity<>(body, headers), String.class).getBody());
    }

    @Test
    void actualManagerAndPythonShareTheDatabaseResourceEnvelope() throws Exception {
        List<Map<String, Object>> peers = new ArrayList<>();
        for (int i = 0; i < 3; i++) {
            long user = 941040001L + i;
            String agent = "mia-p23-" + i, device = "02:00:00:00:23:0" + i, client = "mia-p23-client-" + i;
            db.update("INSERT INTO sys_user(id,username,super_admin,status) VALUES (?,?,0,1)", user, agent);
            db.update("INSERT INTO ai_agent(id,user_id,agent_name) VALUES (?,?,?)", agent, user, "P23 synthetic user");
            db.update("INSERT INTO ai_device(id,mac_address,user_id,agent_id,board,auto_update) VALUES (?,?,?,?,?,0)",
                device, device, user, agent, "MIA_CI");
            String token = tokens.createToken(user).getData().getToken();
            JsonNode code = post("/device/mia-auth/code", Map.of("device_id", device), token);
            assertEquals(0, code.path("code").asInt(-1), "Synthetic authorization code failed");
            JsonNode grant = post("/device/mia-auth/exchange", Map.of("device_id", device, "client_id", client,
                "authorization_code", code.path("data").path("authorization_code").asText()), null);
            assertEquals(0, grant.path("code").asInt(-1), "Synthetic authorization exchange failed");
            peers.add(Map.of("device_id", device, "client_id", client,
                "private_credential", grant.path("data").path("private_credential").asText()));
        }
        ProcessBuilder process = new ProcessBuilder(System.getenv("MIA_P23_PYTHON"),
            System.getenv("MIA_P23_SCRIPT")).redirectErrorStream(true);
        process.redirectOutput(new File(System.getenv("MIA_P23_REPORT_DIR"), "python.log"));
        var env = process.environment();
        env.put("MIA_SCOPE_MANAGER_URL", base() + "/");
        env.put("MIA_SCOPE_SERVER_SECRET", params.getValue("server.secret", false));
        env.put("MIA_P23_PEERS", mapper.writeValueAsString(peers));
        env.put("MIA_P23_MANAGER_PID", Long.toString(ProcessHandle.current().pid()));
        Process running = process.start();
        if (!running.waitFor(900, TimeUnit.SECONDS)) {
            running.destroyForcibly();
            fail("Shared-envelope preflight timed out; inspect sanitized reports");
        }
        assertEquals(0, running.exitValue(), "Shared-envelope measurement failed; inspect reports");
    }
}
