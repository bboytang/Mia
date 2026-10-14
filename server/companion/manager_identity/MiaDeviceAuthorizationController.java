package xiaozhi.modules.device.controller;

import java.util.Map;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import xiaozhi.common.exception.ErrorCode;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.device.service.impl.MiaDeviceAuthorizationService;

@RestController
@RequiredArgsConstructor
public class MiaDeviceAuthorizationController {
    private final MiaDeviceAuthorizationService grants;
    @Value("${mia.private-auth.allow-insecure-test-http:false}")
    private boolean allowInsecureTestHttp;

    private void secure(HttpServletRequest request) {
        if (!request.isSecure() && !allowInsecureTestHttp) throw new RenException(ErrorCode.FORBIDDEN);
    }

    private String field(Map<String, Object> body, String key, int maximum) {
        Object value = body.get(key);
        if (!(value instanceof String text) || text.isBlank() || text.length() > maximum
                || !text.matches("[A-Za-z0-9_:.\\-]+")) throw new RenException(ErrorCode.NO_PERMISSION);
        return (String) value;
    }

    private Result<Map<String, Object>> result(Map<String, Object> value) {
        if (value == null) throw new RenException(ErrorCode.NO_PERMISSION);
        return new Result<Map<String, Object>>().ok(value);
    }

    private long version(Map<String, Object> body, String key) {
        Object value = body.get(key);
        String text = value == null ? "" : value.toString();
        if (!text.matches("[0-9]{1,19}")) throw new RenException(ErrorCode.NO_PERMISSION);
        try {
            return Long.parseLong(text);
        } catch (NumberFormatException invalid) {
            throw new RenException(ErrorCode.NO_PERMISSION);
        }
    }

    @PostMapping("/device/mia-auth/code")
    @RequiresPermissions("sys:role:normal")
    public Result<Map<String, Object>> code(@RequestBody Map<String, Object> body, HttpServletRequest request) {
        secure(request);
        return result(grants.createCode(field(body, "device_id", 32)));
    }

    @PostMapping("/device/mia-auth/exchange")
    public Result<Map<String, Object>> exchange(@RequestBody Map<String, Object> body, HttpServletRequest request) {
        secure(request);
        return result(grants.exchange(field(body, "device_id", 32), field(body, "client_id", 128),
                field(body, "authorization_code", 64), request.getRemoteAddr()));
    }

    @PostMapping("/device/mia-auth/renew")
    public Result<Map<String, Object>> renew(@RequestBody Map<String, Object> body, HttpServletRequest request) {
        secure(request);
        return result(grants.renew(field(body, "device_id", 32), field(body, "client_id", 128),
                field(body, "private_credential", 64), request.getRemoteAddr()));
    }

    @PostMapping("/device/mia-auth/revoke")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> revoke(@RequestBody Map<String, Object> body, HttpServletRequest request) {
        secure(request);
        grants.revoke(field(body, "device_id", 32));
        return new Result<>();
    }

    @PostMapping("/config/mia-auth/verify")
    public Result<Map<String, Object>> verify(@RequestBody Map<String, Object> body) {
        return result(grants.verify(field(body, "device_id", 32), field(body, "client_id", 128),
                field(body, "private_credential", 64)));
    }

    @PostMapping("/config/mia-auth/check-scope")
    public Result<Map<String, Object>> checkScope(@RequestBody Map<String, Object> body) {
        return result(grants.checkScope(field(body, "device_id", 32), field(body, "client_id", 128),
                field(body, "owner", 256), version(body, "operator_id"),
                version(body, "binding_version"), version(body, "credential_version")));
    }
}
