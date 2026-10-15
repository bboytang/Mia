-- Scoring metadata participates in the same query snapshot as facts.
CREATE TRIGGER mia_retrieval_meta_update
AFTER UPDATE OF state,entities,keywords,trigger_terms,emotional_weight ON mia_memory_meta
WHEN OLD.state IS NOT NEW.state OR OLD.entities IS NOT NEW.entities
    OR OLD.keywords IS NOT NEW.keywords OR OLD.trigger_terms IS NOT NEW.trigger_terms
    OR OLD.emotional_weight IS NOT NEW.emotional_weight BEGIN
    UPDATE mia_scope_versions SET content_epoch=content_epoch+1
        WHERE owner=(SELECT owner FROM memories WHERE id=NEW.memory_id);
END;

-- Removed evidence cannot keep contributing derived query clues.
CREATE TRIGGER mia_retrieval_source_delete AFTER DELETE ON sources BEGIN
    UPDATE mia_memory_meta SET entities=NULL,keywords=NULL,trigger_terms=NULL,emotional_weight=NULL
        WHERE memory_id=OLD.memory_id;
END;
