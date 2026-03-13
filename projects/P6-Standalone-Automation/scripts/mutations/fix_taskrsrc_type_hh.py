#!/usr/bin/env python3
"""Corrige RSRC_TYPE a RT_Labor en asignaciones de un proyecto P6.

⚠️  OPERACIÓN DE ESCRITURA — requiere --apply para ejecutar.
"""

import argparse
import sys
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from p6_utils import open_db


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--db', required=True, help='Ruta a DB SQLite P6')
    ap.add_argument('--proj-id', type=int, required=True, help='PROJ_ID objetivo')
    ap.add_argument('--rsrc-id-min', type=int, required=True, help='RSRC_ID mínimo del rango')
    ap.add_argument('--rsrc-id-max', type=int, required=True, help='RSRC_ID máximo del rango')
    ap.add_argument('--apply', action='store_true', help='Aplicar cambios (sin esto es dry-run)')
    args = ap.parse_args()

    con = open_db(args.db)
    cur = con.cursor()

    # Preview
    preview = cur.execute(
        '''
        SELECT TASKRSRC_ID, TASK_ID, RSRC_ID, RSRC_TYPE
        FROM TASKRSRC
        WHERE PROJ_ID = ? AND RSRC_ID BETWEEN ? AND ? AND RSRC_TYPE != 'RT_Labor'
        ''',
        (args.proj_id, args.rsrc_id_min, args.rsrc_id_max)
    ).fetchall()

    print(f'PROJ_ID={args.proj_id}')
    print(f'RSRC_RANGE={args.rsrc_id_min}-{args.rsrc_id_max}')
    print(f'CANDIDATES={len(preview)}')

    if not preview:
        print('NO_CHANGES_NEEDED')
        con.close()
        return

    for r in preview[:20]:
        print(f"  TASKRSRC_ID={r['TASKRSRC_ID']}|RSRC_ID={r['RSRC_ID']}|CURRENT_TYPE={r['RSRC_TYPE']}")

    if len(preview) > 20:
        print(f'  ... y {len(preview) - 20} más')

    if not args.apply:
        print('\nDRY_RUN — usar --apply para ejecutar')
        con.close()
        return

    # Aplicar
    cur.execute(
        '''
        UPDATE TASKRSRC
        SET RSRC_TYPE = 'RT_Labor'
        WHERE PROJ_ID = ? AND RSRC_ID BETWEEN ? AND ?
        ''',
        (args.proj_id, args.rsrc_id_min, args.rsrc_id_max)
    )
    updated = cur.rowcount
    con.commit()
    con.close()

    print(f'\nAPPLIED={updated}')


if __name__ == '__main__':
    main()
