package xiaozhi.modules.device;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.*;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.ActiveProfiles;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import xiaozhi.modules.agent.service.AgentChatSummaryService;
import xiaozhi.modules.llm.service.LLMService;
import xiaozhi.modules.security.service.SysUserTokenService;
import xiaozhi.modules.sys.service.SysParamsService;

/** Real manager/DB/HTTP authorization; synthetic LLM only, not behavior acceptance. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = {"server.servlet.context-path=/xiaozhi", "mia.private-auth.allow-insecure-test-http=true"})
@ActiveProfiles("dev")
class MiaPrivateChatTest {
    private static final long USER = 930000051L;
    private static final String AGENT = "mia-chat-ci-a", OTHER = "mia-chat-ci-b";
    private static final String DEVICE = "02:00:00:00:05:01", CLIENT = "mia-chat-ci-client";
    private static final String SESSION = "mia-chat-ci-session", FOREIGN = "mia-chat-ci-foreign";
    @Autowired private TestRestTemplate http;
    @Autowired private JdbcTemplate db;
    @Autowired private StringRedisTemplate redis;
    @Autowired private SysUserTokenService tokens;
    @Autowired private SysParamsService params;
    @Autowired private ObjectMapper mapper;
    @Autowired private AgentChatSummaryService summaries;
    @MockBean private LLMService llm;
    private String token;
    private Map<String, Object> snapshot;

    @BeforeEach
    void fixtures() throws Exception {
        reset(llm);
        redis.delete(redis.keys("mia:private-auth:*"));
        db.update("DELETE FROM ai_agent_chat_title WHERE session_id IN (?,?)", SESSION, FOREIGN);
        db.update("DELETE FROM ai_agent_chat_history WHERE session_id IN (?,?)", SESSION, FOREIGN);
        db.update("DELETE FROM ai_mia_device_authorization WHERE device_id=?", DEVICE);
        db.update("DELETE FROM ai_device WHERE id=?", DEVICE);
        db.update("DELETE FROM ai_agent WHERE id IN (?,?)", AGENT, OTHER);
        db.update("DELETE FROM sys_user_token WHERE user_id=?", USER);
        db.update("DELETE FROM sys_user WHERE id=?", USER);
        db.update("INSERT INTO sys_user(id,username,super_admin,status) VALUES (?,?,0,1)", USER, "mia-chat-ci-user");
        for (String agent : new String[]{AGENT, OTHER}) {
            db.update("INSERT INTO ai_agent(id,user_id,agent_name,chat_history_conf,summary_memory) VALUES (?,?,?,1,?)",
                    agent, USER, "CI only", "original-" + agent);
        }
        db.update("INSERT INTO ai_device(id,mac_address,user_id,agent_id,board,auto_update) VALUES (?,?,?,?,?,0)",
                DEVICE, DEVICE, USER, AGENT, "MIA_CI");
        token = tokens.createToken(USER).getData().getToken();
        var code = post("/device/mia-auth/code", Map.of("device_id", DEVICE), token);
        assertEquals(0, code.path("code").asInt());
        var exchange = post("/device/mia-auth/exchange", Map.of("device_id", DEVICE, "client_id", CLIENT,
                "authorization_code", code.path("data").path("authorization_code").asText()), null);
        assertEquals(0, exchange.path("code").asInt());
        var proof = post("/config/mia-auth/verify", Map.of("device_id", DEVICE, "client_id", CLIENT,
                "private_credential", exchange.path("data").path("private_credential").asText()), server());
        assertEquals(0, proof.path("code").asInt());
        snapshot = new HashMap<>();
        for (String key : new String[]{"owner", "operator_id", "device_id", "client_id", "binding_version", "credential_version"}) {
            snapshot.put(key, proof.path("data").path(key).asText());
        }
    }

    private String server() { return params.getValue("server.secret", false); }

    private JsonNode post(String path, Map<String, Object> body, String authorization) throws Exception {
        var headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        if (authorization != null) headers.setBearerAuth(authorization);
        var response = http.exchange(path, HttpMethod.POST, new HttpEntity<>(body, headers), String.class);
        assertNotNull(response.getBody());
        return mapper.readTree(response.getBody());
    }

    private Map<String, Object> report(String session) {
        return new HashMap<>(Map.of("macAddress", DEVICE, "sessionId", session, "chatType", 1,
                "content", "我最近喜欢阅读中文小说，周末常去图书馆借书", "miaScope", snapshot));
    }

    private long count(String table) {
        // Fixed test-only table names at all call sites.
        return db.queryForObject("SELECT COUNT(*) FROM " + table + " WHERE session_id=?", Long.class, SESSION);
    }

    private void history(String session, String agent) {
        db.update("INSERT INTO ai_agent_chat_history(mac_address,agent_id,session_id,chat_type,content,created_at) "
                + "VALUES (?,?,?,1,?,NOW())", DEVICE, agent, session, "我最近喜欢阅读中文小说，周末常去图书馆借书");
    }

    private void revoke() throws Exception {
        assertEquals(0, post("/device/mia-auth/revoke", Map.of("device_id", DEVICE), token).path("code").asInt());
    }

    @Test
    void reportRequiresServerSecretAndMatchingSnapshotWithoutChangingExistingBinding() throws Exception {
        var body = report(SESSION);
        assertNotEquals(0, post("/agent/chat-history/report", body, null).path("code").asInt());
        body.remove("miaScope");
        assertNotEquals(0, post("/agent/chat-history/report", body, server()).path("code").asInt());
        body.put("miaScope", snapshot);
        assertEquals(0, post("/agent/chat-history/report", body, server()).path("code").asInt());
        assertEquals(1, count("ai_agent_chat_history"));
        assertEquals(AGENT, db.queryForObject("SELECT agent_id FROM ai_agent_chat_history WHERE session_id=?", String.class, SESSION));
        assertEquals(AGENT, db.queryForObject("SELECT agent_id FROM ai_device WHERE id=?", String.class, DEVICE));
    }

    @Test
    void foreignSessionAndChangedBindingCannotAcceptOldQueuedReports() throws Exception {
        history(FOREIGN, OTHER);
        assertNotEquals(0, post("/agent/chat-history/report", report(FOREIGN), server()).path("code").asInt());
        assertNotEquals(0, post("/agent/chat-title/" + FOREIGN + "/generate", snapshot, server()).path("code").asInt());
        assertNotEquals(0, post("/agent/chat-summary/" + FOREIGN + "/save", snapshot, server()).path("code").asInt());
        db.update("UPDATE ai_device SET agent_id=? WHERE id=?", OTHER, DEVICE);
        assertNotEquals(0, post("/agent/chat-history/report", report(SESSION), server()).path("code").asInt());
        assertEquals(0, count("ai_agent_chat_history"));
        verifyNoInteractions(llm);
    }

    @Test
    void validTitlePersistsButRevokedSnapshotCannotExecute() throws Exception {
        history(SESSION, AGENT);
        when(llm.generateTitle(anyString(), nullable(String.class))).thenReturn("CI阅读标题");
        assertEquals(0, post("/agent/chat-title/" + SESSION + "/generate", snapshot, server()).path("code").asInt());
        assertEquals("CI阅读标题", db.queryForObject("SELECT title FROM ai_agent_chat_title WHERE session_id=?", String.class, SESSION));
        reset(llm);
        revoke();
        assertNotEquals(0, post("/agent/chat-title/" + SESSION + "/generate", snapshot, server()).path("code").asInt());
        assertNotEquals(0, post("/agent/chat-history/report", report(SESSION), server()).path("code").asInt());
        assertFalse(summaries.generateAndSaveChatTitle(SESSION, snapshot));
        assertFalse(summaries.generateAndSaveChatSummary(SESSION, snapshot));
        verifyNoInteractions(llm);
        assertEquals(1, count("ai_agent_chat_history"));
    }

    @Test
    void titleRevokedDuringModelCallCannotCommitAndModelHoldsNoBindingLock() throws Exception {
        history(SESSION, AGENT);
        when(llm.generateTitle(anyString(), nullable(String.class))).thenAnswer(invocation -> {
            revoke(); // Real separate HTTP transaction would time out if the model held DB locks.
            return "must-not-persist";
        });
        assertFalse(summaries.generateAndSaveChatTitle(SESSION, snapshot));
        verify(llm).generateTitle(anyString(), nullable(String.class));
        assertEquals(0, count("ai_agent_chat_title"));
    }

    @Test
    void summaryChangedBindingDuringModelCannotWriteEitherAgent() throws Exception {
        history(SESSION, AGENT);
        db.update("UPDATE ai_agent SET mem_model_id=? WHERE id=?", "Memory_local_short", AGENT);
        when(llm.generateSummaryWithHistory(anyString(), nullable(String.class), nullable(String.class), nullable(String.class)))
                .thenAnswer(invocation -> {
                    db.update("UPDATE ai_device SET agent_id=? WHERE id=?", OTHER, DEVICE);
                    return "CI必须丢弃的摘要";
                });
        assertFalse(summaries.generateAndSaveChatSummary(SESSION, snapshot));
        verify(llm).generateSummaryWithHistory(anyString(), nullable(String.class), nullable(String.class), nullable(String.class));
        for (String agent : new String[]{AGENT, OTHER}) {
            assertEquals("original-" + agent, db.queryForObject("SELECT summary_memory FROM ai_agent WHERE id=?", String.class, agent));
        }
    }
}
