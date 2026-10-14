-- Additive V1.2 structures. memories.content remains the sole fact text.
CREATE TABLE mia_memory_meta (
    memory_id TEXT PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE,
    persona_id TEXT NOT NULL DEFAULT 'mia' CHECK(persona_id='mia'),
    content_version INTEGER NOT NULL DEFAULT 1 CHECK(content_version>0),
    evidence_version INTEGER NOT NULL DEFAULT 1 CHECK(evidence_version>0),
    state TEXT NOT NULL CHECK(state IN ('active','pending','superseded','invalidated')),
    confirmation_origin TEXT NOT NULL DEFAULT 'legacy_unknown',
    entities TEXT, keywords TEXT, trigger_terms TEXT,
    emotional_weight REAL CHECK(emotional_weight>=0 AND emotional_weight<=1)
);
INSERT INTO mia_memory_meta(memory_id,state)
    SELECT id,CASE WHEN confirmed=1 THEN 'active' ELSE 'pending' END FROM memories;

CREATE TABLE mia_scope_versions (
    owner TEXT PRIMARY KEY REFERENCES owners(owner) ON DELETE CASCADE,
    content_epoch INTEGER NOT NULL DEFAULT 0,
    event_epoch INTEGER NOT NULL DEFAULT 0,
    observation_epoch INTEGER NOT NULL DEFAULT 0
);
INSERT INTO mia_scope_versions(owner) SELECT owner FROM owners;

CREATE TABLE mia_source_meta (
    memory_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    turn_id TEXT, message_id TEXT, observed_at INTEGER, source_type TEXT,
    PRIMARY KEY(memory_id,session_id,fingerprint),
    FOREIGN KEY(memory_id,session_id,fingerprint)
        REFERENCES sources(memory_id,session_id,fingerprint) ON DELETE CASCADE
);
INSERT INTO mia_source_meta(memory_id,session_id,fingerprint)
    SELECT memory_id,session_id,fingerprint FROM sources;

CREATE TABLE mia_vectors (
    memory_id TEXT PRIMARY KEY REFERENCES memories(id) ON DELETE CASCADE,
    model_id TEXT NOT NULL, model_revision TEXT NOT NULL,
    dimension INTEGER NOT NULL CHECK(dimension>0),
    content_version INTEGER NOT NULL CHECK(content_version>0),
    normalized_vector BLOB NOT NULL CHECK(length(normalized_vector)=dimension*4),
    indexed_at INTEGER NOT NULL
);

CREATE TABLE mia_associations (
    memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    related_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    relation TEXT NOT NULL, evidence TEXT NOT NULL,
    content_version INTEGER NOT NULL, related_version INTEGER NOT NULL,
    PRIMARY KEY(memory_id,related_id,relation),
    CHECK(memory_id<>related_id)
);
CREATE TRIGGER mia_association_scope BEFORE INSERT ON mia_associations BEGIN
    SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM memories a JOIN memories b ON a.owner=b.owner
        WHERE a.id=NEW.memory_id AND b.id=NEW.related_id)
        THEN RAISE(ABORT,'association_scope_mismatch') END;
END;
CREATE TRIGGER mia_association_scope_update BEFORE UPDATE OF memory_id,related_id ON mia_associations BEGIN
    SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM memories a JOIN memories b ON a.owner=b.owner
        WHERE a.id=NEW.memory_id AND b.id=NEW.related_id)
        THEN RAISE(ABORT,'association_scope_mismatch') END;
END;

CREATE TABLE mia_jobs (
    id TEXT PRIMARY KEY,
    owner TEXT NOT NULL REFERENCES owners(owner) ON DELETE CASCADE,
    idempotency_key TEXT NOT NULL,
    scope_snapshot TEXT NOT NULL, memory_revision INTEGER NOT NULL,
    session_id TEXT NOT NULL, turn_id TEXT NOT NULL,
    source_payload TEXT NOT NULL, validated_result TEXT,
    state TEXT NOT NULL CHECK(state IN ('pending','extracting','validated','retry_wait',
        'committed','empty','cancelled','failed')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK(attempts>=0 AND attempts<=2),
    created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
    deadline INTEGER NOT NULL, next_attempt_at INTEGER, error_category TEXT,
    UNIQUE(owner,idempotency_key)
);
CREATE INDEX mia_jobs_ready ON mia_jobs(state,next_attempt_at,created_at);

CREATE TABLE mia_events (
    id TEXT PRIMARY KEY,
    owner TEXT NOT NULL REFERENCES owners(owner) ON DELETE CASCADE,
    persona_id TEXT NOT NULL DEFAULT 'mia' CHECK(persona_id='mia'),
    event_type TEXT NOT NULL, idempotency_key TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('eligible','pending','active','invalidated')),
    session_id TEXT NOT NULL, turn_id TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
    UNIQUE(owner,persona_id,event_type,idempotency_key)
);
CREATE TABLE mia_event_evidence (
    event_id TEXT NOT NULL REFERENCES mia_events(id) ON DELETE CASCADE,
    memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    content_version INTEGER NOT NULL, evidence_version INTEGER NOT NULL,
    PRIMARY KEY(event_id,memory_id)
);
CREATE TRIGGER mia_event_evidence_scope BEFORE INSERT ON mia_event_evidence BEGIN
    SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM mia_events e JOIN memories m ON e.owner=m.owner
        WHERE e.id=NEW.event_id AND m.id=NEW.memory_id)
        THEN RAISE(ABORT,'event_evidence_scope_mismatch') END;
END;
CREATE TRIGGER mia_event_evidence_scope_update BEFORE UPDATE OF event_id,memory_id ON mia_event_evidence BEGIN
    SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM mia_events e JOIN memories m ON e.owner=m.owner
        WHERE e.id=NEW.event_id AND m.id=NEW.memory_id)
        THEN RAISE(ABORT,'event_evidence_scope_mismatch') END;
END;

CREATE TABLE mia_emotion_consent (
    owner TEXT PRIMARY KEY REFERENCES owners(owner) ON DELETE CASCADE,
    enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)),
    version INTEGER NOT NULL DEFAULT 0,
    enabled_at INTEGER, disabled_at INTEGER
);
CREATE TABLE mia_observations (
    id TEXT PRIMARY KEY,
    owner TEXT NOT NULL REFERENCES owners(owner) ON DELETE CASCADE,
    subject TEXT NOT NULL CHECK(subject='user'),
    source_kind TEXT NOT NULL CHECK(source_kind IN ('self_report','inferred')),
    session_id TEXT NOT NULL, turn_id TEXT NOT NULL, message_id TEXT NOT NULL,
    observed_at INTEGER NOT NULL, created_at INTEGER NOT NULL,
    consent_version INTEGER NOT NULL,
    tendency TEXT NOT NULL, confidence REAL NOT NULL CHECK(confidence>=0 AND confidence<=1),
    source_excerpt TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('active','invalidated')),
    UNIQUE(owner,session_id,message_id,source_kind)
);
CREATE INDEX mia_observations_window ON mia_observations(owner,state,observed_at);

-- Compatibility with unchanged legacy positional inserts and updates.
CREATE TRIGGER mia_owner_insert AFTER INSERT ON owners BEGIN
    INSERT INTO mia_scope_versions(owner) VALUES (NEW.owner);
END;
CREATE TRIGGER mia_memory_insert AFTER INSERT ON memories BEGIN
    INSERT INTO mia_memory_meta(memory_id,state) VALUES (NEW.id,
        CASE WHEN NEW.confirmed=1 THEN 'active' ELSE 'pending' END);
    UPDATE mia_scope_versions SET content_epoch=content_epoch+1 WHERE owner=NEW.owner;
END;
CREATE TRIGGER mia_memory_update AFTER UPDATE OF content,category,confirmed ON memories
WHEN OLD.content<>NEW.content OR OLD.category<>NEW.category OR OLD.confirmed<>NEW.confirmed BEGIN
    UPDATE mia_memory_meta SET content_version=content_version+1,
        state=CASE WHEN NEW.confirmed=1 THEN 'active' ELSE 'pending' END,
        confirmation_origin='legacy_unknown',entities=NULL,keywords=NULL,trigger_terms=NULL,emotional_weight=NULL
        WHERE memory_id=NEW.id;
    DELETE FROM mia_vectors WHERE memory_id=NEW.id;
    DELETE FROM mia_associations WHERE memory_id=NEW.id OR related_id=NEW.id;
    UPDATE mia_scope_versions SET content_epoch=content_epoch+1 WHERE owner=NEW.owner;
    UPDATE mia_events SET state='invalidated',version=version+1,updated_at=NEW.updated_at
        WHERE id IN (SELECT event_id FROM mia_event_evidence WHERE memory_id=NEW.id);
END;
CREATE TRIGGER mia_memory_delete BEFORE DELETE ON memories BEGIN
    DELETE FROM mia_vectors WHERE memory_id=OLD.id;
    DELETE FROM mia_associations WHERE memory_id=OLD.id OR related_id=OLD.id;
    UPDATE mia_events SET state='invalidated',version=version+1
        WHERE id IN (SELECT event_id FROM mia_event_evidence WHERE memory_id=OLD.id);
    UPDATE mia_scope_versions SET content_epoch=content_epoch+1,event_epoch=event_epoch+1 WHERE owner=OLD.owner;
END;
CREATE TRIGGER mia_source_insert AFTER INSERT ON sources BEGIN
    INSERT INTO mia_source_meta(memory_id,session_id,fingerprint) VALUES (NEW.memory_id,NEW.session_id,NEW.fingerprint);
    UPDATE mia_memory_meta SET evidence_version=evidence_version+1 WHERE memory_id=NEW.memory_id;
    UPDATE mia_scope_versions SET content_epoch=content_epoch+1
        WHERE owner=(SELECT owner FROM memories WHERE id=NEW.memory_id);
END;
CREATE TRIGGER mia_source_delete BEFORE DELETE ON sources BEGIN
    UPDATE mia_memory_meta SET evidence_version=evidence_version+1,emotional_weight=NULL WHERE memory_id=OLD.memory_id;
    UPDATE mia_events SET state='invalidated',version=version+1
        WHERE id IN (SELECT event_id FROM mia_event_evidence WHERE memory_id=OLD.memory_id);
    UPDATE mia_scope_versions SET content_epoch=content_epoch+1,event_epoch=event_epoch+1
        WHERE owner=(SELECT owner FROM memories WHERE id=OLD.memory_id);
END;
