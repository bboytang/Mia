CREATE TABLE mia_companion_profile (
    owner TEXT PRIMARY KEY REFERENCES owners(owner) ON DELETE CASCADE,
    enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),
    values_json TEXT NOT NULL,
    version INTEGER NOT NULL CHECK(version>=1),
    updated_at INTEGER NOT NULL
);
CREATE TABLE mia_affect_state_v7 (
    owner TEXT PRIMARY KEY REFERENCES owners(owner) ON DELETE CASCADE,
    valence REAL NOT NULL DEFAULT 0 CHECK(valence BETWEEN -1 AND 1),
    arousal REAL NOT NULL DEFAULT 0.2 CHECK(arousal BETWEEN 0 AND 1),
    tension REAL NOT NULL DEFAULT 0 CHECK(tension BETWEEN 0 AND 1),
    feeling TEXT NOT NULL DEFAULT 'steady' CHECK(feeling IN ('steady','pleased','warm','hurt','guarded','curious','playful','repair','angry')),
    version INTEGER NOT NULL DEFAULT 0 CHECK(version>=0),
    updated_at INTEGER NOT NULL
);
INSERT INTO mia_affect_state_v7 SELECT * FROM mia_affect_state;
DROP TABLE mia_affect_state;
ALTER TABLE mia_affect_state_v7 RENAME TO mia_affect_state;
