package xiaozhi.modules.device;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import xiaozhi.modules.device.controller.OTAController;
import xiaozhi.modules.device.dto.DeviceReportReqDTO;
import xiaozhi.modules.device.dto.DeviceReportRespDTO;
import xiaozhi.modules.device.service.DeviceService;
import xiaozhi.modules.sys.service.SysParamsService;

class YoumiPrivateOtaDiscoveryTest {
    private static final String WSS = "wss://43.143.230.174:8000/xiaozhi/v1/";
    private static final String LEGACY = "ws://43.143.230.174:8000/xiaozhi/v1/";
    private final ObjectMapper mapper = new ObjectMapper();
    private DeviceService devices;
    private OTAController controller;
    private DeviceReportRespDTO response;

    @BeforeEach
    void fixture() {
        devices = mock(DeviceService.class);
        controller = new OTAController(devices, mock(SysParamsService.class));
        response = new DeviceReportRespDTO();
        var websocket = new DeviceReportRespDTO.Websocket();
        websocket.setUrl(WSS);
        websocket.setToken("fixture-token");
        response.setWebsocket(websocket);
        var firmware = new DeviceReportRespDTO.Firmware();
        firmware.setVersion("1.0.4");
        firmware.setUrl("http://43.143.230.174:8002/xiaozhi/otaMag/download/fixture");
        response.setFirmware(firmware);
        when(devices.checkDeviceActive(anyString(), anyString(), any())).thenReturn(response);
    }

    private JsonNode discovery(String board, String version) throws Exception {
        var report = mapper.readValue(mapper.writeValueAsString(java.util.Map.of(
                "board", java.util.Map.of("type", board),
                "application", java.util.Map.of("version", version))), DeviceReportReqDTO.class);
        return mapper.readTree(controller.checkOTAVersion(report, "02:00:00:00:00:01", "fixture").getBody());
    }

    @Test
    void installedPassportCanDiscoverSignedUpgradeWithoutChangingTokens() throws Exception {
        for (String version : new String[]{"1.0.3", "1.0.4"}) {
            response.getWebsocket().setUrl(WSS);
            var result = discovery("mia-ai-passport", version);
            assertEquals(LEGACY, result.at("/websocket/url").asText());
            assertEquals("fixture-token", result.at("/websocket/token").asText());
            assertEquals("1.0.4", result.at("/firmware/version").asText());
            assertEquals(response.getFirmware().getUrl(), result.at("/firmware/url").asText());
        }
        verify(devices, times(2)).checkDeviceActive(anyString(), anyString(), any());
    }

    @Test
    void iphoneAndOtherBoardsKeepWss() throws Exception {
        for (String board : new String[]{"mia-ios", "youmi-ios", "ai-passport", "other"})
            assertEquals(WSS, discovery(board, "1.0.3").at("/websocket/url").asText());
    }

    @Test
    void otherVersionsKeepConfiguredEndpoint() throws Exception {
        for (String version : new String[]{"1.0.2", "1.0.5", "2.0.0", "1.0.30"})
            assertEquals(WSS, discovery("mia-ai-passport", version).at("/websocket/url").asText());
    }

    @Test
    void arbitraryEndpointIsNeverRewritten() throws Exception {
        response.getWebsocket().setUrl("wss://other.example/xiaozhi/v1/");
        assertEquals("wss://other.example/xiaozhi/v1/",
                discovery("mia-ai-passport", "1.0.3").at("/websocket/url").asText());
    }

    @Test
    void activationAndErrorsDoNotAcquireWebsocketCredentials() throws Exception {
        response.setWebsocket(null);
        response.setError("fixture-denied");
        var result = discovery("mia-ai-passport", "1.0.3");
        assertFalse(result.has("websocket"));
        assertEquals("fixture-denied", result.path("error").asText());
    }

    @Test
    void missingReportFieldsLeaveResponseUnchanged() throws Exception {
        var result = mapper.readTree(controller.checkOTAVersion(
                new DeviceReportReqDTO(), "02:00:00:00:00:01", "fixture").getBody());
        assertEquals(WSS, result.at("/websocket/url").asText());
    }

    @Test
    void invalidDeviceStillFailsBeforeDeviceService() throws Exception {
        var result = mapper.readTree(controller.checkOTAVersion(
                new DeviceReportReqDTO(), "invalid", "fixture").getBody());
        assertEquals("Invalid device ID", result.path("error").asText());
        verifyNoInteractions(devices);
    }
}
