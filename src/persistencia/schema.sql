-- Schema SQLite del bot
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    telegram_user_id INTEGER PRIMARY KEY,
    empresa_id       TEXT NOT NULL,
    es_admin         INTEGER NOT NULL DEFAULT 0,
    creado_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS presupuestos (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    id_corto              TEXT NOT NULL UNIQUE,
    empresa_id            TEXT NOT NULL,
    telegram_user_id      INTEGER NOT NULL,
    input_texto           TEXT NOT NULL,
    minimax_json          TEXT,            -- JSON de la respuesta NLU
    minimax_confianza     REAL,
    rubro                 TEXT NOT NULL,
    resultado_json        TEXT NOT NULL,   -- ResultadoPresupuesto serializado
    total                 REAL NOT NULL,
    tokens_input          INTEGER NOT NULL DEFAULT 0,
    tokens_output         INTEGER NOT NULL DEFAULT 0,
    usd_estimado          REAL NOT NULL DEFAULT 0,
    latencia_ms           INTEGER NOT NULL DEFAULT 0,
    pdf_path              TEXT,
    creado_at             TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_presupuestos_empresa ON presupuestos(empresa_id, creado_at);
CREATE INDEX IF NOT EXISTS idx_presupuestos_rubro ON presupuestos(empresa_id, rubro);

CREATE TABLE IF NOT EXISTS feedback (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    presupuesto_id   INTEGER NOT NULL REFERENCES presupuestos(id) ON DELETE CASCADE,
    preciso          INTEGER NOT NULL,       -- 1 = sí, 0 = no
    total_real       REAL,                    -- si corrigió
    nota             TEXT,
    creado_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_feedback_presupuesto ON feedback(presupuesto_id);

CREATE TABLE IF NOT EXISTS tokens_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha           TEXT NOT NULL DEFAULT (date('now')),
    tokens_input    INTEGER NOT NULL DEFAULT 0,
    tokens_output   INTEGER NOT NULL DEFAULT 0,
    usd_estimado    REAL NOT NULL DEFAULT 0,
    calls           INTEGER NOT NULL DEFAULT 0,
    UNIQUE(fecha)
);

-- Sesiones conversacionales (TTL 30 minutos)
CREATE TABLE IF NOT EXISTS sesiones (
    telegram_user_id  INTEGER PRIMARY KEY,
    empresa_id        TEXT NOT NULL,
    accion            TEXT NOT NULL,
    params_json       TEXT NOT NULL,
    resultado_id      INTEGER REFERENCES presupuestos(id) ON DELETE SET NULL,
    updated_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Conversaciones por empresa para contexto extendida
CREATE TABLE IF NOT EXISTS conversaciones (
    telegram_user_id INTEGER PRIMARY KEY,
    empresa_id       TEXT NOT NULL,
    mensajes_json    TEXT NOT NULL DEFAULT '[]',
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
