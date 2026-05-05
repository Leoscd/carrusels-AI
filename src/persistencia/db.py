"""Capa delgada sobre SQLite (stdlib, async-safe via aiosqlite-like pattern sincrónico)."""
from __future__ import annotations

import json
import sqlite3
import secrets
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from src.config import settings
from src.rubros.base import ResultadoPresupuesto

SCHEMA = Path(__file__).parent / "schema.sql"


def _conectar() -> sqlite3.Connection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with _conectar() as conn:
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))


@contextmanager
def cursor() -> Iterator[sqlite3.Cursor]:
    conn = _conectar()
    try:
        yield conn.cursor()
    finally:
        conn.close()


# ---- Usuarios ----

def vincular_usuario(telegram_user_id: int, empresa_id: str, es_admin: bool = False) -> None:
    with cursor() as c:
        c.execute(
            "INSERT INTO usuarios(telegram_user_id, empresa_id, es_admin) "
            "VALUES(?,?,?) ON CONFLICT(telegram_user_id) DO UPDATE SET "
            "empresa_id=excluded.empresa_id, es_admin=excluded.es_admin",
            (telegram_user_id, empresa_id, int(es_admin)),
        )


def empresa_de(telegram_user_id: int) -> str | None:
    with cursor() as c:
        row = c.execute(
            "SELECT empresa_id FROM usuarios WHERE telegram_user_id=?",
            (telegram_user_id,),
        ).fetchone()
    return row["empresa_id"] if row else None


# ---- Presupuestos ----

def guardar_presupuesto(
    *,
    empresa_id: str,
    telegram_user_id: int,
    input_texto: str,
    minimax_json: dict | None,
    minimax_confianza: float | None,
    resultado: ResultadoPresupuesto,
    tokens_input: int = 0,
    tokens_output: int = 0,
    usd_estimado: float = 0.0,
    latencia_ms: int = 0,
    pdf_path: str | None = None,
) -> tuple[int, str]:
    id_corto = secrets.token_hex(3).upper()
    with cursor() as c:
        c.execute(
            """INSERT INTO presupuestos
               (id_corto, empresa_id, telegram_user_id, input_texto,
                minimax_json, minimax_confianza, rubro, resultado_json, total,
                tokens_input, tokens_output, usd_estimado, latencia_ms, pdf_path)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                id_corto,
                empresa_id,
                telegram_user_id,
                input_texto,
                json.dumps(minimax_json, ensure_ascii=False) if minimax_json else None,
                minimax_confianza,
                resultado.rubro,
                resultado.model_dump_json(),
                float(resultado.total),
                tokens_input,
                tokens_output,
                usd_estimado,
                latencia_ms,
                pdf_path,
            ),
        )
        pid = int(c.lastrowid or 0)
    return pid, id_corto


def guardar_feedback(
    presupuesto_id: int, preciso: bool, total_real: float | None = None, nota: str | None = None
) -> None:
    with cursor() as c:
        c.execute(
            "INSERT INTO feedback(presupuesto_id, preciso, total_real, nota) VALUES(?,?,?,?)",
            (presupuesto_id, int(preciso), total_real, nota),
        )


# ---- Outliers ----

def mediana_total(empresa_id: str, rubro: str, n: int = 20) -> float | None:
    with cursor() as c:
        rows = c.execute(
            "SELECT total FROM presupuestos WHERE empresa_id=? AND rubro=? "
            "ORDER BY id DESC LIMIT ?",
            (empresa_id, rubro, n),
        ).fetchall()
    if len(rows) < 5:
        return None
    vals = sorted(r["total"] for r in rows)
    m = len(vals) // 2
    return vals[m] if len(vals) % 2 else (vals[m - 1] + vals[m]) / 2


# ---- Tokens ----

def acumular_tokens(tokens_in: int, tokens_out: int, usd: float) -> None:
    with cursor() as c:
        c.execute(
            """INSERT INTO tokens_log(tokens_input, tokens_output, usd_estimado, calls)
               VALUES(?,?,?,1)
               ON CONFLICT(fecha) DO UPDATE SET
                 tokens_input = tokens_input + excluded.tokens_input,
                 tokens_output = tokens_output + excluded.tokens_output,
                 usd_estimado = usd_estimado + excluded.usd_estimado,
                 calls = calls + 1""",
            (tokens_in, tokens_out, usd),
        )


def usd_total_gastado() -> float:
    with cursor() as c:
        row = c.execute("SELECT COALESCE(SUM(usd_estimado), 0) AS t FROM tokens_log").fetchone()
    return float(row["t"])


def stats_admin() -> dict[str, Any]:
    with cursor() as c:
        row_tok = c.execute(
            "SELECT COALESCE(SUM(tokens_input),0) AS ti, COALESCE(SUM(tokens_output),0) AS to_,"
            " COALESCE(SUM(usd_estimado),0) AS usd, COALESCE(SUM(calls),0) AS calls"
            " FROM tokens_log"
        ).fetchone()
        row_p = c.execute("SELECT COUNT(*) AS n FROM presupuestos").fetchone()
    return {
        "presupuestos": row_p["n"],
        "tokens_input": row_tok["ti"],
        "tokens_output": row_tok["to_"],
        "calls_minimax": row_tok["calls"],
        "usd_gastado": round(row_tok["usd"], 4),
        "usd_restante": round(settings.minimax_budget_usd - row_tok["usd"], 4),
    }


# ---- Sesiones conversacionales ----

def guardar_sesion(
    telegram_user_id: int,
    empresa_id: str,
    accion: str,
    params: dict,
    resultado_id: int | None = None,
) -> None:
    """Guarda o actualiza la sesión activa del usuario."""
    with cursor() as c:
        c.execute(
            """INSERT INTO sesiones(telegram_user_id, empresa_id, accion, params_json, resultado_id, updated_at)
               VALUES(?, ?, ?, ?, ?, datetime('now'))
               ON CONFLICT(telegram_user_id) DO UPDATE SET
                 empresa_id=excluded.empresa_id,
                 accion=excluded.accion,
                 params_json=excluded.params_json,
                 resultado_id=excluded.resultado_id,
                 updated_at=datetime('now')""",
            (telegram_user_id, empresa_id, accion, json.dumps(params, ensure_ascii=False), resultado_id),
        )


def obtener_sesion(telegram_user_id: int) -> dict | None:
    """Devuelve la sesión activa si existe y no expiró (30 min). None si no hay."""
    with cursor() as c:
        row = c.execute(
            """SELECT accion, params_json, resultado_id, updated_at
               FROM sesiones
               WHERE telegram_user_id=?
                 AND updated_at > datetime('now', '-30 minutes')""",
            (telegram_user_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "accion": row["accion"],
        "params": json.loads(row["params_json"]),
        "resultado_id": row["resultado_id"],
        "updated_at": row["updated_at"],
    }


def limpiar_sesion(telegram_user_id: int) -> None:
    """Elimina la sesión activa del usuario (inicio de nuevo presupuesto)."""
    with cursor() as c:
        c.execute("DELETE FROM sesiones WHERE telegram_user_id=?", (telegram_user_id,))


# ---- Historial conversacional (contexto extendido) ----

def cargar_historial(telegram_user_id: int) -> list[dict]:
    """Carga el historial de mensajes para un usuario.
    
    Devuelve lista de dicts con {rol: "user"|"assistant", contenido: str, timestamp: str}.
    """
    with cursor() as c:
        row = c.execute(
            "SELECT mensajes_json FROM conversaciones WHERE telegram_user_id=?",
            (telegram_user_id,),
        ).fetchone()
    if row is None:
        return []
    return json.loads(row["mensajes_json"])


def guardar_historial(
    telegram_user_id: int,
    empresa_id: str,
    mensajes: list[dict],
) -> None:
    """Guarda o actualiza el historial de mensajes para un usuario.
    
    Args:
        telegram_user_id: ID del usuario de Telegram.
        empresa_id: ID de la empresa activa.
        mensajes: Lista de dicts [{rol: "user"|"assistant", contenido: str}, ...].
    """
    with cursor() as c:
        c.execute(
            """INSERT INTO conversaciones(telegram_user_id, empresa_id, mensajes_json, updated_at)
               VALUES(?, ?, ?, datetime('now'))
               ON CONFLICT(telegram_user_id) DO UPDATE SET
                 empresa_id=excluded.empresa_id,
                 mensajes_json=excluded.mensajes_json,
                 updated_at=datetime('now')""",
            (
                telegram_user_id,
                empresa_id,
                json.dumps(mensajes, ensure_ascii=False),
            ),
        )


def limpiar_historial(telegram_user_id: int) -> None:
    """Elimina todo el historial de mensajes del usuario."""
    with cursor() as c:
        c.execute("DELETE FROM conversaciones WHERE telegram_user_id=?", (telegram_user_id,))
