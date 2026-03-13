#!/usr/bin/env python3
"""Inspecciona estructura WBS de un proyecto P6."""

import argparse
import sys
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from p6_utils import open_db


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--db', required=True, help='Ruta a DB SQLite P6')
    ap.add_argument('--proj-id', type=int, required=True, help='PROJ_ID a inspeccionar')
    ap.add_argument('--limit', type=int, default=15, help='Máximo de filas a mostrar')
    args = ap.parse_args()

    con = open_db(args.db)
    cur = con.cursor()

    rows = cur.execute(
        'SELECT WBS_ID, PARENT_WBS_ID, WBS_SHORT_NAME, WBS_NAME, SEQ_NUM '
        'FROM PROJWBS WHERE PROJ_ID=? ORDER BY SEQ_NUM, WBS_ID',
        (args.proj_id,)
    ).fetchall()

    print(f'COUNT={len(rows)}')
    for r in rows[:args.limit]:
        print(f"{r['WBS_ID']}|{r['PARENT_WBS_ID']}|{r['WBS_SHORT_NAME']}|{r['WBS_NAME']}")

    # Detectar raíces
    ids = set(r['WBS_ID'] for r in rows)
    roots = [r for r in rows if r['PARENT_WBS_ID'] is None or r['PARENT_WBS_ID'] not in ids or r['PARENT_WBS_ID'] == r['WBS_ID']]
    print(f'ROOTS={len(roots)}')
    for r in roots[:10]:
        print(f"ROOT|{r['WBS_ID']}|{r['PARENT_WBS_ID']}|{r['WBS_SHORT_NAME']}")

    con.close()


if __name__ == '__main__':
    main()
