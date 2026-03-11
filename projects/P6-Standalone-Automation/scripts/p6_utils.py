"""
p6_utils.py — Utilidades compartidas para scripts P6-Standalone-Automation.

Centraliza:
- Conexión SQLite con row_factory
- Timestamp formateado
- División en 3 con corrección de redondeo
- Payload de clonación de recurso
- Gestión de NEXTKEY (get/set)
- Inserción genérica de filas
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


RSRC_CLEAR_FIELDS = (
    "USER_ID",
    "GUID",
    "RSRC_SEQ_NUM",
    "EMAIL_ADDR",
    "EMPLOYEE_CODE",
    "OFFICE_PHONE",
    "OTHER_PHONE",
    "RSRC_NOTES",
    "TS_APPROVE_USER_ID",
    "DELETE_SESSION_ID",
    "DELETE_DATE",
)


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def open_db(path: str | Path) -> sqlite3.Connection:
    db = Path(path)
    if not db.exists():
        raise FileNotFoundError(f"Base de datos no encontrada: {db}")
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    return con


def get_next_id(cur: sqlite3.Cursor, key_name: str) -> int:
    row = cur.execute(
        "SELECT KEY_SEQ_NUM FROM NEXTKEY WHERE KEY_NAME=?",
        (key_name,),
    ).fetchone()
    if not row:
        raise RuntimeError(f"NEXTKEY '{key_name}' no encontrado en la base de datos")
    return int(row[0] if not hasattr(row, 'keys') else row["KEY_SEQ_NUM"])


def set_next_id(cur: sqlite3.Cursor, key_name: str, value: int) -> None:
    cur.execute(
        "UPDATE NEXTKEY SET KEY_SEQ_NUM=?, UPDATE_DATE=?, UPDATE_USER=? WHERE KEY_NAME=?",
        (value, now_str(), "openclaw", key_name),
    )


def split3(v: float) -> list[float]:
    a = round(v / 3.0, 4)
    b = round(v / 3.0, 4)
    c = round(v - a - b, 4)
    return [a, b, c]


def clone_resource_payload(
    template: sqlite3.Row,
    rsrc_id: int,
    short_name: str,
    name: str,
    title: str = "HH",
    rsrc_type: str = "RT_Labor",
) -> dict:
    d = dict(template)
    d["RSRC_ID"] = rsrc_id
    d["RSRC_SHORT_NAME"] = short_name[:255]
    d["RSRC_NAME"] = name[:255]
    d["RSRC_TITLE_NAME"] = title
    d["RSRC_TYPE"] = rsrc_type
    d["ACTIVE_FLAG"] = "Y"
    d["CREATE_DATE"] = now_str()
    d["CREATE_USER"] = "openclaw"
    d["UPDATE_DATE"] = now_str()
    d["UPDATE_USER"] = "openclaw"

    for field in RSRC_CLEAR_FIELDS:
        if field in d:
            d[field] = None

    return d


def insert_row(cur: sqlite3.Cursor, table: str, row_dict: dict) -> None:
    cols = list(row_dict.keys())
    marks = ",".join(["?"] * len(cols))
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({marks})"
    cur.execute(sql, [row_dict[c] for c in cols])
