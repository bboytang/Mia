-- Bounded real interaction evidence, separate from the authoritative fact text.
CREATE TABLE mia_event_interactions (
    event_id TEXT PRIMARY KEY REFERENCES mia_events(id) ON DELETE CASCADE,
    user_excerpt TEXT NOT NULL,
    assistant_excerpt TEXT,
    source_fingerprint TEXT NOT NULL,
    observed_at INTEGER NOT NULL
);

CREATE TABLE mia_observation_meta (
    observation_id TEXT PRIMARY KEY REFERENCES mia_observations(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    source_fingerprint TEXT NOT NULL,
    correction_origin TEXT
);

CREATE TRIGGER mia_event_state_update AFTER UPDATE OF state,version ON mia_events
WHEN OLD.state IS NOT NEW.state OR OLD.version IS NOT NEW.version BEGIN
    UPDATE mia_scope_versions SET event_epoch=event_epoch+1 WHERE owner=NEW.owner;
    UPDATE mia_event_interactions SET user_excerpt='',assistant_excerpt=NULL
        WHERE event_id=NEW.id AND NEW.state='invalidated';
END;
CREATE TRIGGER mia_event_insert AFTER INSERT ON mia_events BEGIN
    UPDATE mia_scope_versions SET event_epoch=event_epoch+1 WHERE owner=NEW.owner;
END;
CREATE TRIGGER mia_event_delete AFTER DELETE ON mia_events BEGIN
    UPDATE mia_scope_versions SET event_epoch=event_epoch+1 WHERE owner=OLD.owner;
END;
CREATE TRIGGER mia_observation_insert AFTER INSERT ON mia_observations BEGIN
    UPDATE mia_scope_versions SET observation_epoch=observation_epoch+1 WHERE owner=NEW.owner;
END;
CREATE TRIGGER mia_observation_update AFTER UPDATE ON mia_observations BEGIN
    UPDATE mia_scope_versions SET observation_epoch=observation_epoch+1 WHERE owner=NEW.owner;
END;
CREATE TRIGGER mia_observation_delete AFTER DELETE ON mia_observations BEGIN
    UPDATE mia_scope_versions SET observation_epoch=observation_epoch+1 WHERE owner=OLD.owner;
END;
CREATE TRIGGER mia_consent_insert AFTER INSERT ON mia_emotion_consent BEGIN
    UPDATE mia_scope_versions SET observation_epoch=observation_epoch+1 WHERE owner=NEW.owner;
END;
CREATE TRIGGER mia_consent_update AFTER UPDATE ON mia_emotion_consent BEGIN
    UPDATE mia_scope_versions SET observation_epoch=observation_epoch+1 WHERE owner=NEW.owner;
END;

-- Legacy source edits/deletes also retract observations tied to that evidence.
CREATE TRIGGER mia_observation_source_delete BEFORE DELETE ON sources BEGIN
    UPDATE mia_observations SET state='invalidated',source_excerpt=''
    WHERE owner=(SELECT owner FROM memories WHERE id=OLD.memory_id)
      AND (source_excerpt=OLD.excerpt OR EXISTS (
        SELECT 1 FROM mia_source_meta s WHERE s.memory_id=OLD.memory_id
          AND s.session_id=OLD.session_id AND s.fingerprint=OLD.fingerprint
          AND s.session_id=mia_observations.session_id
          AND (s.message_id=mia_observations.message_id OR s.turn_id=mia_observations.turn_id)));
    UPDATE mia_events SET state='invalidated',version=version+1
    WHERE owner=(SELECT owner FROM memories WHERE id=OLD.memory_id)
      AND EXISTS (SELECT 1 FROM mia_source_meta s WHERE s.memory_id=OLD.memory_id
        AND s.session_id=OLD.session_id AND s.fingerprint=OLD.fingerprint
        AND s.session_id=mia_events.session_id AND s.turn_id=mia_events.turn_id);
END;
