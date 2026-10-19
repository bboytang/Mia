CREATE TABLE mia_feature_settings (
    owner TEXT PRIMARY KEY REFERENCES owners(owner) ON DELETE CASCADE,
    memory_recall INTEGER NOT NULL DEFAULT 1 CHECK(memory_recall IN (0,1)),
    personality_growth INTEGER NOT NULL DEFAULT 1 CHECK(personality_growth IN (0,1)),
    interaction_events INTEGER NOT NULL DEFAULT 1 CHECK(interaction_events IN (0,1))
);
