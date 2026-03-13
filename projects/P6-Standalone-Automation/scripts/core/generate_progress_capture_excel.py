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
    'Actividad ID',
    'Actividad',
    'Estado P6',
    'Color estado',
    'Entrega / WBS nivel 3',
    'WBS completa',
    '% Complete Type',
    'Calendar ID',
    'Inicio plan',
    'Término plan',
    'BAC HH',
    'EV HH',
    'ETC HH',
    '% avance a cargar',
    'Fecha inicio real a cargar',
    'Fecha término si 100%',
    'Notas usuario',
]

STATUS_LABELS = {
    'TK_Complete': 'Complete',
    'TK_Active': 'Active',
    'TK_NotStart': 'NotStart',
}

STATUS_FILLS = {
    'TK_Complete': PatternFill('solid', fgColor='C6EFCE'),
    'TK_Active': PatternFill('solid', fgColor='FFF2CC'),
    'TK_NotStart': PatternFill('solid', fgColor='F4CCCC'),
}

HEADER_FILL = PatternFill('solid', fgColor='1F4E78')
HEADER_FONT = Font(color='FFFFFF', bold=True)
HEADER_ALIGN = Alignment(horizontal='center', vertical='center', wrap_text=True)
WRAP_ALIGN = Alignment(vertical='top', wrap_text=True)


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


def build_wbs_maps(cur: sqlite3.Cursor, proj_id: int) -> tuple[dict[int, sqlite3.Row], dict[int, str], dict[int, str]]:
    rows = cur.execute(
        '''
        SELECT WBS_ID, PARENT_WBS_ID, WBS_SHORT_NAME, WBS_NAME
        FROM PROJWBS
        WHERE PROJ_ID = ?
        ''',
        (proj_id,),
    ).fetchall()
    by_id = {int(r['WBS_ID']): r for r in rows}
    full_map: dict[int, str] = {}
    lvl3_map: dict[int, str] = {}

    def compose(wbs_id: int | None) -> tuple[str, str]:
        if not wbs_id or wbs_id not in by_id:
            return '', ''
        if wbs_id in full_map:
            return full_map[wbs_id], lvl3_map[wbs_id]
        parts: list[str] = []
        chain: list[sqlite3.Row] = []
        current = by_id[wbs_id]
        seen: set[int] = set()
        while current and int(current['WBS_ID']) not in seen:
            seen.add(int(current['WBS_ID']))
            chain.append(current)
            parent_id = current['PARENT_WBS_ID']
            current = by_id.get(int(parent_id)) if parent_id is not None and int(parent_id) in by_id else None
        chain.reverse()
        for item in chain:
            short = (item['WBS_SHORT_NAME'] or '').strip()
            name = (item['WBS_NAME'] or '').strip()
            label = short if short and short != name else name or short
            if label:
                parts.append(label)
        full = ' > '.join(parts)
        entrega = parts[2] if len(parts) >= 3 else (parts[-1] if parts else '')
        full_map[wbs_id] = full
        lvl3_map[wbs_id] = entrega
        return full, entrega

    for wbs_id in by_id:
        compose(wbs_id)
    return by_id, full_map, lvl3_map


def style_header(ws) -> None:
    ws.row_dimensions[1].height = 32
    for col_idx, _ in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = HEADER_ALIGN


def apply_status_style(ws, row_idx: int, status_code: str) -> None:
    fill = STATUS_FILLS.get(status_code)
    if not fill:
        return
    for col_idx in range(1, len(HEADERS) + 1):
        ws.cell(row=row_idx, column=col_idx).fill = fill


def build_instructions_sheet(wb: Workbook) -> None:
    ws = wb.create_sheet('Instrucciones')
    rows = [
        ('Objetivo', 'Usa esta hoja para capturar el avance real de la semana sin modificar datos base del programa.'),
        ('Qué mirar primero', 'Revisa Estado P6, Entrega / WBS nivel 3 y WBS completa para ubicar exactamente la actividad antes de cargar avance.'),
        ('Columnas a modificar', 'Solo editar: % avance a cargar, Fecha inicio real a cargar, Fecha término si 100%, Notas usuario.'),
        ('No modificar', 'No cambiar Actividad ID, Actividad, Estado P6, WBS, % Complete Type, Calendar ID, Inicio/Término plan, BAC/EV/ETC HH.'),
        ('Regla avance parcial', 'Si la actividad avanza pero NO termina: ingresar % avance a cargar y Fecha inicio real a cargar. Dejar vacía Fecha término si 100%.'),
        ('Regla cierre 100%', 'Si la actividad termina en la semana: ingresar 100 en % avance a cargar, Fecha inicio real a cargar y Fecha término si 100%.'),
        ('Fechas', 'Si escribes una fecha sin hora, el cargador intentará normalizarla usando la lógica planificada/calendario. Igual conviene revisar casos especiales.'),
        ('Estados por color', 'Verde = Complete, Amarillo = Active, Rojo = NotStart.'),
        ('WBS / Entrega', 'Entrega / WBS nivel 3 resume a qué paquete pertenece la actividad. WBS completa muestra el camino completo para evitar confusiones.'),
        ('Recomendación', 'Completa primero las actividades Active y las que realmente trabajaron en W11. Evita marcar 100% si no tienes fecha real de término.'),
    ]
    ws.append(['Campo', 'Detalle'])
    for item in rows:
        ws.append(list(item))
    style_header(ws)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = WRAP_ALIGN
    auto_fit(ws)
    ws.column_dimensions['A'].width = 24
    ws.column_dimensions['B'].width = 110
    ws.freeze_panes = 'A2'


def build_meta_sheet(wb: Workbook, proj: sqlite3.Row, args, week_start: date, week_end: date, count_rows: int) -> None:
    ws = wb.create_sheet('Meta')
    ws.append(['Campo', 'Valor'])
    ws.append(['PROJ_ID', proj['PROJ_ID']])
    ws.append(['Programa', proj['PROJ_SHORT_NAME'] or ''])
    ws.append(['Semana ISO solicitada', args.iso_week])
    ws.append(['Desde', str(week_start)])
    ws.append(['Hasta', str(week_end)])
    ws.append(['LAST_SCHEDULE_DATE', proj['LAST_SCHEDULE_DATE'] or ''])
    ws.append(['Filas generadas', count_rows])
    ws.append(['Criterio', 'Actividades task con HH labor y solape de fechas plan/labor con la semana ISO'])
    style_header(ws)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = WRAP_ALIGN
    auto_fit(ws)
    ws.column_dimensions['A'].width = 28
    ws.column_dimensions['B'].width = 90
    ws.freeze_panes = 'A2'


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

    _, wbs_full_map, wbs_lvl3_map = build_wbs_maps(cur, args.proj_id)

    rows = cur.execute(
        '''
        SELECT
            t.TASK_ID,
            t.TASK_CODE,
            t.TASK_NAME,
            t.STATUS_CODE,
            t.WBS_ID,
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
            t.TASK_ID, t.TASK_CODE, t.TASK_NAME, t.STATUS_CODE, t.WBS_ID,
            COALESCE(t.COMPLETE_PCT_TYPE, p.DEF_COMPLETE_PCT_TYPE),
            t.CLNDR_ID, t.TARGET_START_DATE, t.TARGET_END_DATE
        ORDER BY COALESCE(t.WBS_ID, 0), t.TASK_CODE
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
    style_header(ws)

    for row in selected:
        plan_start = parse_db_dt(row['LABOR_START']) or parse_db_dt(row['TARGET_START_DATE'])
        plan_end = parse_db_dt(row['LABOR_END']) or parse_db_dt(row['TARGET_END_DATE'])
        wbs_id = int(row['WBS_ID']) if row['WBS_ID'] is not None else None
        wbs_full = wbs_full_map.get(wbs_id or -1, '')
        wbs_lvl3 = wbs_lvl3_map.get(wbs_id or -1, '')
        status_code = row['STATUS_CODE'] or ''
        status_label = STATUS_LABELS.get(status_code, status_code)

        ws.append([
            row['TASK_CODE'],
            row['TASK_NAME'],
            status_label,
            status_label,
            wbs_lvl3,
            wbs_full,
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
            '',
        ])
        row_idx = ws.max_row
        apply_status_style(ws, row_idx, status_code)
        for col_idx in range(1, len(HEADERS) + 1):
            ws.cell(row=row_idx, column=col_idx).alignment = WRAP_ALIGN

    ws.freeze_panes = 'A2'
    ws.auto_filter.ref = f'A1:{get_column_letter(len(HEADERS))}{ws.max_row}'
    ws.column_dimensions['B'].width = 48
    ws.column_dimensions['E'].width = 28
    ws.column_dimensions['F'].width = 80
    ws.column_dimensions['N'].width = 18
    ws.column_dimensions['O'].width = 22
    ws.column_dimensions['P'].width = 22
    ws.column_dimensions['Q'].width = 28
    auto_fit(ws)

    build_instructions_sheet(wb)
    build_meta_sheet(wb, proj, args, week_start, week_end, len(selected))

    wb.save(out_path)
    print(f'OUT_XLSX={out_path}')
    print(f'ROWS={len(selected)}')
    print(f'PROJ_ID={proj["PROJ_ID"]}')
    print(f'PROG={proj["PROJ_SHORT_NAME"]}')
    print(f'WEEK_START={week_start}')
    print(f'WEEK_END={week_end}')


if __name__ == '__main__':
    main()