package xiaozhi.modules.device;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.client.TestRestTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import com.fasterxml.jackson.databind.ObjectMapper;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
        properties = "server.servlet.context-path=/xiaozhi")
@ActiveProfiles("dev")
class MiaPrivateTransportTest {
    @Autowired private TestRestTemplate http;
    @Autowired private ObjectMapper mapper;

    @Test
    void defaultPublicGrantEndpointsRejectPlainHttpAndUntrustedForwardedProto() throws Exception {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.set("X-Forwarded-Proto", "https");
        for (String operation : new String[]{"exchange", "renew"}) {
            var body = Map.of("device_id", "02:00:00:00:04:01", "client_id", "mia-tls-ci",
                    "authorization_code", "not-issued", "private_credential", "not-issued");
            var response = http.exchange("/device/mia-auth/" + operation, HttpMethod.POST,
                    new HttpEntity<>(body, headers), String.class);
            var result = mapper.readTree(response.getBody());
            assertEquals(403, result.path("code").asInt());
            assertFalse(result.path("data").has("private_credential"));
        }
    }
}
