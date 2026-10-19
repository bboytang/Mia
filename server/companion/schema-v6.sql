ALTER TABLE mia_feature_settings ADD COLUMN companion_emotion INTEGER NOT NULL DEFAULT 0 CHECK(companion_emotion IN (0,1));
CREATE TABLE mia_affect_state (
    owner TEXT PRIMARY KEY REFERENCES owners(owner) ON DELETE CASCADE,
    valence REAL NOT NULL DEFAULT 0 CHECK(valence BETWEEN -1 AND 1),
    arousal REAL NOT NULL DEFAULT 0.2 CHECK(arousal BETWEEN 0 AND 1),
    tension REAL NOT NULL DEFAULT 0 CHECK(tension BETWEEN 0 AND 1),
    feeling TEXT NOT NULL DEFAULT 'steady' CHECK(feeling IN ('steady','pleased','warm','hurt','guarded','curious','playful','repair')),
    version INTEGER NOT NULL DEFAULT 0 CHECK(version>=0),
    updated_at INTEGER NOT NULL
);
CREATE TABLE mia_affect_turns (
    owner TEXT NOT NULL REFERENCES owners(owner) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    turn_id TEXT NOT NULL,
    source_sha256 TEXT NOT NULL,
    feeling TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY(owner,session_id,turn_id)
);
