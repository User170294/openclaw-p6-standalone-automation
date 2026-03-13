#!/usr/bin/env python3
import argparse
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
import sys

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from p6_utils import open_db

SHEET_NAME = 'Revision_Avance_W012'
HEADERS = [
    'Actividad ID',
    'Actividad',
    'Estado P6',
    '% Complete Type',
    'Calendar ID',
    'Inicio plan',
    'TÃƒÂ©rmino plan',
    'BAC HH',
    'EV HH',
    'ETC HH',
    '% avance a cargar',
    'Fecha inicio real a cargar',
    'Fecha tÃƒÂ©rmino si 100%',
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description='Genera Excel de captura de avances semanales desde DB SQLite de P6.')
    ap.add_argument('--db', required=True)
    ap.add_argument('--proj-id', type=int, required=True)
    ap.add_argument('--iso-week', required=True, help='Formato ISO YYYY-W##, ej. 2026-W11')
    ap.add_argument('--sheet', default=SHEET_NAME)
    ap.add_argument('--out', required=True, help='Ruta xlsx de salida')
    return ap.parse_args()


def iso_week_bounds(iso_week: str) -> tuple[date, date]:
    txt = iso_week.strip().upper().replace('ISO', '')
    year_s, week_s = txt.split('-W')
    year = int(year_s)
    week = int(week_s)
    start = date.fromisocalendar(year, week, 1)
    end = date.fromisocalendar(year, week, 7)
    return start, end


def parse_db_dt(value: Any) -> datetime | None:
    if value in (None, ''):
        return None
    txt = str(value)
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f'):
        try:
            return datetime.strptime(txt, fmt)
        except ValueError:
            pass
    raise ValueError(f'Fecha DB no reconocida: {value!r}')


def overlaps(start_a: datetime | None, end_a: datetime | None, start_b: datetime, end_b: datetime) -> bool:
    if start_a is None and end_a is None:
        return False
    left = start_a or end_a
    right = end_a or start_a
    if left is None or right is None:
        return False
    return left <= end_b and right >= start_b


def auto_fit(ws):
    widths: dict[int, int] = {}
    for row in ws.iter_rows(values_only=True):
        for idx, value in enumerate(row, start=1):
            size = len(str(value)) if value is not None else 0
            widths[idx] = max(widths.get(idx, 0), min(size + 2, 50))
    for idx, width in widths.items():
        ws.column_dimensions[get_column_letter(idx)].width = width


def main() -> None:
    args = parse_args()
    week_start, week_end = iso_week_bounds(args.iso_week)
    dt_start = datetime.combine(week_start, datetime.min.time())
    dt_end = datetime.combine(week_end, datetime.max.time().replace(microsecond=0))

    con = open_db(args.db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    proj = cur.execute(
        '''
        SELECT PROJ_ID, PROJ_SHORT_NAME, LAST_SCHEDULE_DATE, DEF_COMPLETE_PCT_TYPE
        FROM PROJECT
        WHERE PROJ_ID = ?
        ''',
        (args.proj_id,),
    ).fetchone()
    if not proj:
        raise SystemExit(f'PROJ_ID no encontrado: {args.proj_id}')

    rows = cur.execute(
        '''
        SELECT
            t.TASK_ID,
            t.TASK_CODE,
            t.TASK_NAME,
            t.STATUS_CODE,
            COALESCE(t.COMPLETE_PCT_TYPE, p.DEF_COMPLETE_PCT_TYPE) AS COMPLETE_PCT_TYPE,
            t.CLNDR_ID,
            t.TARGET_START_DATE,
            t.TARGET_END_DATE,
            COALESCE(SUM(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN tr.TARGET_QTY ELSE 0 END), 0) AS BAC_HH,
            COALESCE(SUM(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN COALESCE(tr.ACT_REG_QTY,0) + COALESCE(tr.ACT_OT_QTY,0) ELSE 0 END), 0) AS EV_HH,
            COALESCE(SUM(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN COALESCE(tr.REMAIN_QTY,0) ELSE 0 END), 0) AS ETC_HH,
            MIN(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN tr.TARGET_START_DATE END) AS LABOR_START,
            MAX(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN tr.TARGET_END_DATE END) AS LABOR_END,
            SUM(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN 1 ELSE 0 END) AS LABOR_ROWS
        FROM TASK t
        JOIN PROJECT p ON p.PROJ_ID = t.PROJ_ID
        LEFT JOIN TASKRSRC tr ON tr.PROJ_ID = t.PROJ_ID AND tr.TASK_ID = t.TASK_ID
        WHERE t.PROJ_ID = ?
          AND COALESCE(t.TASK_TYPE, '') NOT IN ('TT_Mile', 'TT_FinMile', 'TT_LOE', 'TT_WBS')
        GROUP BY
            t.TASK_ID, t.TASK_CODE, t.TASK_NAME, t.STATUS_CODE,
            COALESCE(t.COMPLETE_PCT_TYPE, p.DEF_COMPLETE_PCT_TYPE),
            t.CLNDR_ID, t.TARGET_START_DATE, t.TARGET_END_DATE
        ORDER BY t.TASK_CODE
        ''',
        (args.proj_id,),
    ).fetchall()
    con.close()

    selected: list[sqlite3.Row] = []
    for row in rows:
        if float(row['BAC_HH'] or 0) <= 0 or int(row['LABOR_ROWS'] or 0) <= 0:
            continue
        plan_start = parse_db_dt(row['LABOR_START']) or parse_db_dt(row['TARGET_START_DATE'])
        plan_end = parse_db_dt(row['LABOR_END']) or parse_db_dt(row['TARGET_END_DATE'])
        if not overlaps(plan_start, plan_end, dt_start, dt_end):
            continue
        selected.append(row)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = args.sheet
    ws.append(HEADERS)

    header_fill = PatternFill('solid', fgColor='1F4E78')
    header_font = Font(color='FFFFFF', bold=True)
    for col_idx, header in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font

    for row in selected:
        plan_start = parse_db_dt(row['LABOR_START']) or parse_db_dt(row['TARGET_START_DATE'])
        plan_end = parse_db_dt(row['LABOR_END']) or parse_db_dt(row['TARGET_END_DATE'])
        ws.append([
            row['TASK_CODE'],
            row['TASK_NAME'],
            row['STATUS_CODE'] or '',
            row['COMPLETE_PCT_TYPE'] or '',
            row['CLNDR_ID'] or '',
            plan_start.strftime('%Y-%m-%d %H:%M:%S') if plan_start else '',
            plan_end.strftime('%Y-%m-%d %H:%M:%S') if plan_end else '',
            float(row['BAC_HH'] or 0),
            float(row['EV_HH'] or 0),
            float(row['ETC_HH'] or 0),
            '',
            '',
            '',
        ])

    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f'A1:{get_column_letter(len(HEADERS))}{ws.max_row}'
    auto_fit(ws)

    meta = wb.create_sheet('Meta')
    meta.append(['Campo', 'Valor'])
    meta.append(['PROJ_ID', proj['PROJ_ID']])
    meta.append(['Programa', proj['PROJ_SHORT_NAME'] or ''])
    meta.append(['Nombre', proj['PROJ_SHORT_NAME'] or ''])
    meta.append(['Semana ISO solicitada', args.iso_week])
    meta.append(['Desde', str(week_start)])
    meta.append(['Hasta', str(week_end)])
    meta.append(['LAST_SCHEDULE_DATE', proj['LAST_SCHEDULE_DATE'] or ''])
    meta.append(['Filas generadas', len(selected)])
    meta.append(['Criterio', 'Actividades task con HH labor y solape de fechas plan/labor con la semana ISO'])
    auto_fit(meta)

    wb.save(out_path)
    print(f'OUT_XLSX={out_path}')
    print(f'ROWS={len(selected)}')
    print(f'PROJ_ID={proj["PROJ_ID"]}')
    print(f'PROG={proj["PROJ_SHORT_NAME"]}')
    print(f'WEEK_START={week_start}')
    print(f'WEEK_END={week_end}')


if __name__ == '__main__':
    main()
