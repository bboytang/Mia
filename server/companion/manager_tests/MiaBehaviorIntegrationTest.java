package xiaozhi.modules.device;

import static org.junit.jupiter.api.Assertions.*;

import java.net.URI;
import java.util.Map;
import java.util.List;
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
    "server.servlet.context-path=/xiaozhi", "server.ssl.enabled=true",
    "server.ssl.key-store=${MIA_SCOPE_KEYSTORE}", "server.ssl.key-store-password=mia-ci-only",
    "server.ssl.key-store-type=PKCS12", "mia.private-auth.allow-insecure-test-http=false",
    "logging.level.root=ERROR"
})
@ActiveProfiles("dev")
class MiaBehaviorIntegrationTest {
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
        return mapper.readTree(http.exchange(path, HttpMethod.POST, new HttpEntity<>(body, headers), String.class).getBody());
    }

    private Map<String, Object> peer(long user, String token, String agent, String device, String client, String kind) throws Exception {
        db.update("INSERT INTO ai_device(id,mac_address,user_id,agent_id,board,auto_update) VALUES (?,?,?,?,?,0)",
            device, device, user, agent, "MIA_CI");
        JsonNode code = post("/device/mia-auth/code", Map.of("device_id", device), token);
        assertEquals(0, code.path("code").asInt());
        JsonNode grant = post("/device/mia-auth/exchange", Map.of("device_id", device, "client_id", client,
            "authorization_code", code.path("data").path("authorization_code").asText()), null);
        assertEquals(0, grant.path("code").asInt());
        return Map.of("kind", kind, "device_id", device, "client_id", client, "agent_id", agent,
            "private_credential", grant.path("data").path("private_credential").asText());
    }

    @Test
    void threeIndependentUsersUseActualSelectedProviderAndPersistentVoiceBridge() throws Exception {
        String key = System.getenv("MIA_TEST_LLM_API_KEY");
        String endpoint = System.getenv("MIA_TEST_LLM_BASE_URL");
        String model = System.getenv("MIA_TEST_LLM_MODEL");
        String baselineModel = model;
        String comparisonModel = System.getenv().getOrDefault("MIA_TEST_MODEL_OVERRIDE", "");
        if (!comparisonModel.isBlank()) {
            assertTrue(comparisonModel.equals("glm-5.3-flash") || comparisonModel.equals("glm-5.3-flashx") || comparisonModel.equals("glm-4.7-flash") || comparisonModel.equals("glm-4-flash-250414"),
                "Unapproved isolated comparison model");
            model = comparisonModel;
        }
        String suite = System.getenv().getOrDefault("MIA_BEHAVIOR_SUITE", "continuity");
        assertTrue(suite.equals("continuity") || suite.equals("growth") || suite.equals("scope") || suite.equals("faults") || suite.equals("shutdown") || suite.equals("emotions") || suite.equals("tools") || suite.equals("correction") || suite.equals("natural_correction") || suite.equals("retrieval") || suite.equals("retrieval_holdout") || suite.equals("retrieval_holdout_v3") || suite.equals("inflight") || suite.equals("recovery"));
        assertNotNull(key, "Dedicated test provider not configured");
        assertNotNull(endpoint, "Dedicated test endpoint not configured");
        assertNotNull(model, "Dedicated test model not configured");
        URI uri = URI.create(endpoint);
        assertTrue("https".equals(uri.getScheme()) && uri.getHost() != null && uri.getUserInfo() == null
            && uri.getQuery() == null && uri.getFragment() == null, "Invalid dedicated HTTPS test endpoint");
        String selected = "LLM_MiaBehavior";
        String configuration = mapper.writeValueAsString(Map.of("type", "openai", "api_key", key,
            "base_url", endpoint, "model_name", model, "max_tokens", comparisonModel.isBlank() ? 768 : 4096,
            "temperature", 0.1, "timeout", 30));
        db.update("DELETE FROM ai_model_config WHERE id=?", selected);
        db.update("INSERT INTO ai_model_config(id,model_type,model_code,model_name,is_default,is_enabled,config_json,sort) VALUES (?,'LLM','openai','Mia isolated behavior',0,1,?,999)", selected, configuration);
        boolean passed = true;
        String selectedRound = System.getenv().getOrDefault("MIA_EMOTION_DIAGNOSTIC_ROUND", "all");
        assertTrue(selectedRound.equals("all") || (suite.equals("emotions")
            && List.of("0", "1", "2").contains(selectedRound)), "Single-round selection is emotion diagnostics only");
        for (int round = 0; round < 3; round++) {
            if (!selectedRound.equals("all") && !selectedRound.equals(Integer.toString(round))) continue;
            long user = 941010001L + round;
            String agent = "mia-behavior-" + round;
            String device = "02:00:00:00:07:0" + round, client = "mia-behavior-client-" + round;
            db.update("INSERT INTO sys_user(id,username,super_admin,status) VALUES (?,?,0,1)", user, agent);
            db.update("INSERT INTO ai_agent(id,user_id,agent_name,system_prompt,llm_model_id) VALUES (?,?,?,?,?)",
                agent, user, "Synthetic behavior user", "用自然简短的中文聊天。", selected);
            db.update("INSERT INTO ai_device(id,mac_address,user_id,agent_id,board,auto_update) VALUES (?,?,?,?,?,0)",
                device, device, user, agent, "MIA_CI");
            String token = tokens.createToken(user).getData().getToken();
            JsonNode code = post("/device/mia-auth/code", Map.of("device_id", device), token);
            assertEquals(0, code.path("code").asInt());
            JsonNode grant = post("/device/mia-auth/exchange", Map.of("device_id", device, "client_id", client,
                "authorization_code", code.path("data").path("authorization_code").asText()), null);
            assertEquals(0, grant.path("code").asInt());
            ProcessBuilder process = new ProcessBuilder("python", System.getenv("MIA_BEHAVIOR_SCRIPT")).redirectErrorStream(true);
            var env = process.environment();
            env.put("MIA_TEST_LLM_MODEL", model);
            env.put("MIA_TEST_LLM_BASELINE_MODEL", baselineModel);
            env.put("MIA_SCOPE_MANAGER_URL", base() + "/");
            env.put("MIA_SCOPE_SERVER_SECRET", params.getValue("server.secret", false));
            env.put("MIA_SCOPE_DEVICE", device);
            env.put("MIA_SCOPE_CLIENT", client);
            env.put("MIA_SCOPE_CREDENTIAL", grant.path("data").path("private_credential").asText());
            env.put("MIA_SCOPE_USER_TOKEN", token);
            env.put("MIA_BEHAVIOR_ROUND", Integer.toString(round));
            env.put("MIA_BEHAVIOR_SUITE", suite);
            if (suite.equals("scope")) {
                long otherUser = 941020001L + round;
                String otherAgent = agent + "-other", foreignAgent = agent + "-foreign";
                db.update("INSERT INTO sys_user(id,username,super_admin,status) VALUES (?,?,0,1)", otherUser, foreignAgent);
                for (var entry : Map.of(otherAgent, user, foreignAgent, otherUser).entrySet()) {
                    db.update("INSERT INTO ai_agent(id,user_id,agent_name,system_prompt,llm_model_id) VALUES (?,?,?,?,?)",
                        entry.getKey(), entry.getValue(), "Synthetic scope user", "用自然简短的中文聊天。", selected);
                }
                env.put("MIA_BEHAVIOR_PEERS", mapper.writeValueAsString(List.of(
                    peer(user, token, agent, "02:00:00:00:08:0" + round, client + "-shared", "shared_device"),
                    peer(user, token, otherAgent, "02:00:00:00:09:0" + round, client + "-agent", "other_agent"),
                    peer(otherUser, tokens.createToken(otherUser).getData().getToken(), foreignAgent,
                        "02:00:00:00:0a:0" + round, client + "-user", "other_user"))));
            }
            Process running = process.start();
            if (!running.waitFor(300, TimeUnit.SECONDS)) {
                running.destroyForcibly();
                fail("Bounded real-provider behavior round timed out");
            }
            String output = new String(running.getInputStream().readAllBytes(), java.nio.charset.StandardCharsets.UTF_8);
            System.out.println(output);
            passed &= running.exitValue() == 0;
        }
        assertTrue(passed, "Actual manager/BGE/provider behavior failed; inspect sanitized reports");
    }
}
