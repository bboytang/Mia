package xiaozhi.modules.device.service.impl;

import java.util.Map;
import java.util.function.Supplier;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

import lombok.RequiredArgsConstructor;
import youmi.common.exception.ErrorCode;
import youmi.common.exception.RenException;

/** Guards the existing report/title/summary writes; model calls hold no DB locks. */
@Service
@RequiredArgsConstructor
public class YoumiChatAuthorizationService {
    private final YoumiDeviceAuthorizationService grants;
    private final JdbcTemplate db;
    private final PlatformTransactionManager transactions;

    public Map<String, Object> require(Map<String, Object> snapshot, String session, boolean allowEmpty) {
        Map<String, Object> scope = grants.requireSnapshot(snapshot, false);
        session(scope, session, allowEmpty);
        return scope;
    }

    private void session(Map<String, Object> scope, String session, boolean allowEmpty) {
        if (session == null || !session.matches("[A-Za-z0-9_-]{1,64}")) {
            throw new RenException(ErrorCode.NO_PERMISSION);
        }
        var counts = db.queryForMap("SELECT COUNT(*) AS total, COALESCE(SUM(CASE WHEN "
                + "BINARY agent_id=BINARY ? AND BINARY mac_address=BINARY ? THEN 0 ELSE 1 END),0) AS mismatched "
                + "FROM ai_agent_chat_history WHERE session_id=?", scope.get("agent_id"), scope.get("device_id"), session);
        if ((!allowEmpty && ((Number) counts.get("total")).longValue() == 0)
                || ((Number) counts.get("mismatched")).longValue() != 0) {
            throw new RenException(ErrorCode.NO_PERMISSION);
        }
    }

    public <T> T write(Map<String, Object> snapshot, String session, boolean allowEmpty, Supplier<T> writer) {
        return new TransactionTemplate(transactions).execute(status -> {
            // Same device -> grant lock order as binding/revocation; short commit only.
            Map<String, Object> scope = grants.requireSnapshot(snapshot, true);
            session(scope, session, allowEmpty);
            return writer.get();
        });
    }
}
