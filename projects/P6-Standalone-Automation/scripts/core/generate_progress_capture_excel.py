#!/usr/bin/env python3
import argparse
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any
import sys

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from p6_utils import open_db

SHEET_NAME = 'Revision_Avance_W012'
HEADERS = [
    'Entrega',
    'Despacho/Tag',
    'WBS',
    'Actividad ID',
    'Actividad',
    'Estado P6',
    'BAC HH',
    'EV HH',
    'Avance %',
    'Marcar avance',
    'Fecha inicio real (si estaba TK_NotStart)',
    'Fecha termino real (si queda 100%)',
    'Observaciones',
]

HEADER_FILL = PatternFill('solid', fgColor='1F4E78')
HEADER_FONT = Font(color='FFFFFF', bold=True)
HEADER_ALIGN = Alignment(horizontal='center', vertical='center', wrap_text=True)
WRAP_ALIGN = Alignment(vertical='top', wrap_text=True)

STATUS_FILLS = {
    'TK_Complete': PatternFill('solid', fgColor='E2F0D9'),
    'TK_Active': PatternFill('solid', fgColor='FFF2CC'),
    'TK_NotStart': PatternFill('solid', fgColor='FCE4D6'),
}

INSTRUCTIONS = [
    ('Objetivo', 'Capturar avance real W11 con la misma logica de la planilla operativa validada anteriormente.'),
    ('Que revisar primero', 'Ubicar la actividad por Entrega, Despacho/Tag y WBS antes de marcar avance.'),
    ('Color por estado', 'Verde = TK_Complete, Amarillo = TK_Active, Rojo = TK_NotStart.'),
    ('Que editar', 'Editar solo: Marcar avance, Fecha inicio real (si estaba TK_NotStart), Fecha termino real (si queda 100%), Observaciones.'),
    ('Regla TK_NotStart', 'Si una actividad estaba TK_NotStart y la comienzas, debes informar Fecha inicio real.'),
    ('Regla cierre 100%', 'Si una actividad queda al 100%, debes informar Fecha termino real. Si ademas estaba TK_NotStart, informar tambien Fecha inicio real.'),
    ('Regla TK_Active', 'Si la actividad ya estaba iniciada y solo agregas avance al corte, no modificar fechas; solo Marcar avance y, si aplica, Observaciones.'),
    ('Mismo dia inicio y termino', 'Si una actividad inicia y termina el mismo dia, se interpreta como jornada completa: inicio al comienzo de la jornada y termino al final de la jornada.'),
    ('Lectura de avance', 'Avance % se calcula como EV HH / BAC HH y sirve de referencia del estado actual de la DB.'),
    ('Uso recomendado', 'Filtrar primero por Entrega o por Despacho/Tag para trabajar una entrega a la vez.'),
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


def auto_fit(ws) -> None:
    widths: dict[int, int] = {}
    for row in ws.iter_rows(values_only=True):
        for idx, value in enumerate(row, start=1):
            size = len(str(value)) if value is not None else 0
            widths[idx] = max(widths.get(idx, 0), min(size + 2, 80))
    for idx, width in widths.items():
        ws.column_dimensions[get_column_letter(idx)].width = width


def style_header(ws, headers: list[str]) -> None:
    ws.row_dimensions[1].height = 34
    for col_idx, _ in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = HEADER_ALIGN


def clean_label(short_name: str | None, name: str | None) -> str:
    short = (short_name or '').strip()
    name = (name or '').strip()
    if short and name and short != name:
        return f'{short} | {name}'
    return name or short


def build_wbs_map(cur: sqlite3.Cursor, proj_id: int) -> dict[int, list[str]]:
    rows = cur.execute(
        '''
        SELECT WBS_ID, PARENT_WBS_ID, WBS_SHORT_NAME, WBS_NAME
        FROM PROJWBS
        WHERE PROJ_ID = ?
        ''',
        (proj_id,),
    ).fetchall()
    by_id = {int(r['WBS_ID']): r for r in rows}
    chain_map: dict[int, list[str]] = {}

    def compose(wbs_id: int | None) -> list[str]:
        if not wbs_id or wbs_id not in by_id:
            return []
        if wbs_id in chain_map:
            return chain_map[wbs_id]
        chain_rows: list[sqlite3.Row] = []
        current = by_id[wbs_id]
        seen: set[int] = set()
        while current and int(current['WBS_ID']) not in seen:
            seen.add(int(current['WBS_ID']))
            chain_rows.append(current)
            parent_id = current['PARENT_WBS_ID']
            current = by_id.get(int(parent_id)) if parent_id is not None and int(parent_id) in by_id else None
        chain_rows.reverse()
        labels = [clean_label(r['WBS_SHORT_NAME'], r['WBS_NAME']) for r in chain_rows if clean_label(r['WBS_SHORT_NAME'], r['WBS_NAME'])]
        chain_map[wbs_id] = labels
        return labels

    for wbs_id in by_id:
        compose(wbs_id)
    return chain_map


def normalize_tag(raw: str) -> str:
    raw = raw.strip()
    if '|' in raw:
        _, cleaned = raw.split('|', 1)
        return cleaned.strip()
    return raw


def normalize_wbs(raw: str) -> str:
    raw = raw.strip()
    if '|' in raw:
        short_name, name = raw.split('|', 1)
        short_name = short_name.strip()
        name = name.strip()
        if short_name.isdigit():
            return name
    return raw


def derive_structure(parts: list[str]) -> tuple[str, str, str]:
    entrega = ''
    despacho_tag = ''
    wbs = ''
    if len(parts) >= 3:
        despacho_tag = normalize_tag(parts[2])
        if despacho_tag.endswith('-1'):
            entrega = 'Entrega 1'
        elif despacho_tag.endswith('-2'):
            entrega = 'Entrega 2'
        elif despacho_tag.endswith('-3'):
            entrega = 'Entrega 3'
        elif despacho_tag.endswith('-4'):
            entrega = 'Entrega 4'
        elif despacho_tag.endswith('-5'):
            entrega = 'Entrega 5'
        else:
            entrega = despacho_tag
    if len(parts) >= 4:
        wbs = normalize_wbs(parts[3])
    return entrega, despacho_tag, wbs


def build_instructions_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet('Instrucciones')
    ws.append(['Campo', 'Detalle'])
    style_header(ws, ['Campo', 'Detalle'])
    for item in INSTRUCTIONS:
        ws.append(list(item))
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = WRAP_ALIGN
    ws.freeze_panes = 'A2'
    ws.column_dimensions['A'].width = 28
    ws.column_dimensions['B'].width = 120


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
        SELECT PROJ_ID, PROJ_SHORT_NAME, LAST_SCHEDULE_DATE
        FROM PROJECT
        WHERE PROJ_ID = ?
        ''',
        (args.proj_id,),
    ).fetchone()
    if not proj:
        raise SystemExit(f'PROJ_ID no encontrado: {args.proj_id}')

    chain_map = build_wbs_map(cur, args.proj_id)

    rows = cur.execute(
        '''
        SELECT
            t.TASK_ID,
            t.TASK_CODE,
            t.TASK_NAME,
            t.STATUS_CODE,
            t.WBS_ID,
            t.TARGET_START_DATE,
            t.TARGET_END_DATE,
            COALESCE(SUM(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN tr.TARGET_QTY ELSE 0 END), 0) AS BAC_HH,
            COALESCE(SUM(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN COALESCE(tr.ACT_REG_QTY,0) + COALESCE(tr.ACT_OT_QTY,0) ELSE 0 END), 0) AS EV_HH,
            MIN(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN tr.TARGET_START_DATE END) AS LABOR_START,
            MAX(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN tr.TARGET_END_DATE END) AS LABOR_END,
            SUM(CASE WHEN tr.RSRC_TYPE='RT_Labor' THEN 1 ELSE 0 END) AS LABOR_ROWS
        FROM TASK t
        LEFT JOIN TASKRSRC tr ON tr.PROJ_ID = t.PROJ_ID AND tr.TASK_ID = t.TASK_ID
        WHERE t.PROJ_ID = ?
          AND COALESCE(t.TASK_TYPE, '') NOT IN ('TT_Mile', 'TT_FinMile', 'TT_LOE', 'TT_WBS')
        GROUP BY t.TASK_ID, t.TASK_CODE, t.TASK_NAME, t.STATUS_CODE, t.WBS_ID, t.TARGET_START_DATE, t.TARGET_END_DATE
        ORDER BY COALESCE(t.WBS_ID, 0), t.TASK_CODE
        ''',
        (args.proj_id,),
    ).fetchall()
    con.close()

    selected: list[dict[str, Any]] = []
    for row in rows:
        if float(row['BAC_HH'] or 0) <= 0 or int(row['LABOR_ROWS'] or 0) <= 0:
            continue
        plan_start = parse_db_dt(row['LABOR_START']) or parse_db_dt(row['TARGET_START_DATE'])
        plan_end = parse_db_dt(row['LABOR_END']) or parse_db_dt(row['TARGET_END_DATE'])
        if not overlaps(plan_start, plan_end, dt_start, dt_end):
            continue
        parts = chain_map.get(int(row['WBS_ID'])) if row['WBS_ID'] is not None else []
        entrega, despacho_tag, wbs = derive_structure(parts or [])
        bac = float(row['BAC_HH'] or 0)
        ev = float(row['EV_HH'] or 0)
        pct = round((ev / bac), 4) if bac else 0.0
        selected.append({
            'entrega': entrega,
            'despacho_tag': despacho_tag,
            'wbs': wbs,
            'task_code': row['TASK_CODE'],
            'task_name': row['TASK_NAME'],
            'status_code': row['STATUS_CODE'] or '',
            'bac_hh': bac,
            'ev_hh': ev,
            'avance_pct': pct,
        })

    selected.sort(key=lambda r: (r['entrega'], r['despacho_tag'], r['wbs'], r['task_code']))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = args.sheet
    ws.append(HEADERS)
    style_header(ws, HEADERS)

    for item in selected:
        ws.append([
            item['entrega'],
            item['despacho_tag'],
            item['wbs'],
            item['task_code'],
            item['task_name'],
            item['status_code'],
            item['bac_hh'],
            item['ev_hh'],
            item['avance_pct'],
            '',
            '',
            '',
            '',
        ])
        row_idx = ws.max_row
        fill = STATUS_FILLS.get(item['status_code'])
        if fill:
            for col_idx in range(1, len(HEADERS) + 1):
                ws.cell(row_idx, col_idx).fill = fill
        for col_idx in range(1, len(HEADERS) + 1):
            ws.cell(row_idx, col_idx).alignment = WRAP_ALIGN

    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f'A1:{get_column_letter(len(HEADERS))}{ws.max_row}'
    ws.column_dimensions['A'].width = 14
    ws.column_dimensions['B'].width = 28
    ws.column_dimensions['C'].width = 28
    ws.column_dimensions['D'].width = 14
    ws.column_dimensions['E'].width = 48
    ws.column_dimensions['F'].width = 14
    ws.column_dimensions['J'].width = 16
    ws.column_dimensions['K'].width = 24
    ws.column_dimensions['L'].width = 24
    ws.column_dimensions['M'].width = 28
    auto_fit(ws)

    build_instructions_sheet(wb)
    wb.save(out_path)

    print(f'OUT_XLSX={out_path}')
    print(f'ROWS={len(selected)}')
    print(f'PROJ_ID={proj["PROJ_ID"]}')
    print(f'PROG={proj["PROJ_SHORT_NAME"]}')
    print(f'WEEK_START={week_start}')
    print(f'WEEK_END={week_end}')
    print('FORMAT_PROFILE=OT1844_DB_LOAD_CAPTURE_V1_ASCII_SAFE')


if __name__ == '__main__':
    main()
