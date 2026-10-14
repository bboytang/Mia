"""One atomic additive migration; legacy fact tables and positional writes stay valid."""

import hashlib
import json
from pathlib import Path
import sqlite3
import time


LEGACY_COLUMNS = {
    'owners': ['owner', 'revision', 'paused', 'version'],
    'memories': ['id', 'owner', 'category', 'content', 'confirmed', 'created_at', 'updated_at'],
    'sources': ['memory_id', 'session_id', 'fingerprint', 'excerpt', 'created_at'],
    'traits': ['owner', 'name', 'description', 'evidence_ids', 'updated_at'],
    'checkpoints': ['owner', 'checkpoint_id', 'created_at'],
}


def _statements(source):
    pending = ''
    for line in source.splitlines(True):
        pending += line
        if sqlite3.complete_statement(pending):
            yield pending
            pending = ''
    if pending.strip():
        raise ValueError('Incomplete Mia schema statement')


def migrate(db):
    if db.in_transaction:
        raise ValueError('Mia schema migration requires its own transaction')
    sql = Path(__file__).with_name('schema.sql').read_text(encoding='utf-8')
    digest = hashlib.sha256(sql.encode()).hexdigest()
    db.execute('BEGIN IMMEDIATE')
    try:
        for table, expected in LEGACY_COLUMNS.items():
            actual = [row[1] for row in db.execute(f'PRAGMA table_info({table})')]
            if actual != expected:
                raise ValueError(f'Unreviewed legacy memory schema: {table}')
        exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='mia_schema_migrations'").fetchone()
        if exists:
            rows = db.execute('SELECT version,checksum,schema_checksum FROM mia_schema_migrations ORDER BY version').fetchall()
            if (len(rows) != 1 or (rows[0][0], rows[0][1]) != (1, digest)
                    or rows[0][2] != _schema_checksum(db)):
                raise ValueError('Unreviewed Mia schema version or checksum')
            db.commit()
            return
        if db.execute("SELECT 1 FROM sqlite_master WHERE name GLOB 'mia_*' LIMIT 1").fetchone():
            raise ValueError('Unversioned Mia schema objects; refusing to overwrite')
        db.execute('CREATE TABLE mia_schema_migrations(version INTEGER PRIMARY KEY,checksum TEXT NOT NULL,schema_checksum TEXT NOT NULL,applied_at INTEGER NOT NULL)')
        # executescript() implicitly commits; execute complete DDL statements instead.
        for statement in _statements(sql):
            db.execute(statement)
        db.execute('INSERT INTO mia_schema_migrations(version,checksum,schema_checksum,applied_at) VALUES (1,?,?,?)',
                   (digest, _schema_checksum(db), int(time.time())))
        db.commit()
    except BaseException:
        db.rollback()
        raise


def _schema_checksum(db):
    objects = [tuple(row) for row in db.execute(
        "SELECT type,name,sql FROM sqlite_master WHERE name GLOB 'mia_*' ORDER BY type,name")]
    return hashlib.sha256(json.dumps(objects, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
