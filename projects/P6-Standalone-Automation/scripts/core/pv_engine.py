from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta, date, time
from pathlib import Path
from typing import Any
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from p6_utils import open_db
from report_generator import generate_report


DEFAULT_WEEK0 = date(2026, 2, 16)  # ancla vigente OT-1844 para labels W##
FIXED_COLUMNS = ['week', 'pv_week', 'pv_cum', 'pv_pct', 'ev_cum', 'ev_pct', 'sv', 'spi', 'forecast_cum', 'forecast_pct']


def week_label(mon: date, anchor: date = DEFAULT_WEEK0) -> str:
    delta = (mon - anchor).days
    week_num = 8 + delta // 7
    return f'W{week_num:02d}'


def parse_table(path: str | Path, table_name: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    cur = None
    fields = None
    with Path(path).open('r', encoding='latin-1', errors='ignore') as fh:
        for raw in fh:
            ln = raw.rstrip('\n\r')
            if not ln:
                continue
            parts = ln.split('\t')
            tag = parts[0]
            if tag == '%T':
                cur = parts[1] if len(parts) > 1 else ''
                fields = None
            elif tag == '%F' and cur == table_name:
                fields = parts[1:]
            elif tag == '%R' and cur == table_name and fields:
                vals = parts[1:]
                if len(vals) < len(fields):
                    vals += [''] * (len(fields) - len(vals))
                rows.append(dict(zip(fields, vals)))
    return rows


def safe_float(x: Any) -> float:
    if x is None or x == '':
        return 0.0
    try:
        return float(x)
    except Exception:
        return 0.0


def safe_dt(s: str | None) -> datetime | None:
    if not s or not str(s).strip():
        return None
    s = str(s).strip()
    candidates = [s, s[:19], s[:16], s[:10]]
    for candidate in candidates:
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
            try:
                return datetime.strptime(candidate, fmt)
            except Exception:
                pass
    return None


def spread_lv(start_d: date | None, end_d: date | None, qty: float, bucket: dict[date, float]) -> None:
    if not start_d or not end_d or end_d < start_d or qty <= 0:
        return
    days: list[date] = []
    d = start_d
    while d <= end_d:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    if not days:
        days = [start_d]
    per = qty / len(days)
    for day in days:
        mon = day - timedelta(days=day.weekday())
        bucket[mon] = bucket.get(mon, 0.0) + per


def excel_serial_to_date(serial: int) -> date:
    return (datetime(1899, 12, 30) + timedelta(days=int(serial))).date()


def parse_clock(value: str) -> time:
    return datetime.strptime(value, '%H:%M').time()


def combine_dt(day: date, clock: time) -> datetime:
    return datetime(day.year, day.month, day.day, clock.hour, clock.minute, clock.second)


def parse_calendar_text(raw: Any) -> dict[str, Any]:
    text = '' if raw is None else str(raw)
    if text.startswith("b'") and text.endswith("'"):
        text = text[2:-1].encode('latin-1', errors='ignore').decode('unicode_escape', errors='ignore')
    else:
        text = text.encode('latin-1', errors='ignore').decode('latin-1', errors='ignore')

    weekday_windows: dict[int, list[tuple[time, time]]] = defaultdict(list)
    exceptions: set[date] = set()

    days_start = text.find('DaysOfWeek()(')
    view_start = text.find('(0||VIEW', days_start if days_start >= 0 else 0)
    days_text = text[days_start:view_start] if days_start >= 0 and view_start > days_start else text

    markers = list(re.finditer(r'\(0\|\|([1-7])\(\)', days_text))
    for idx, match in enumerate(markers):
        p6_day = int(match.group(1))
        body_start = match.end()
        body_end = markers[idx + 1].start() if idx + 1 < len(markers) else len(days_text)
        body = days_text[body_start:body_end]
        py_weekday = (p6_day + 5) % 7  # P6: 1=Sun .. 7=Sat  -> Python: Mon=0 .. Sun=6
        for s_txt, f_txt in re.findall(r's\|(\d{2}:\d{2})\|f\|(\d{2}:\d{2})', body):
            weekday_windows[py_weekday].append((parse_clock(s_txt), parse_clock(f_txt)))

    for serial_txt in re.findall(r'd\|(\d+)', text):
        exceptions.add(excel_serial_to_date(int(serial_txt)))

    for wd in list(weekday_windows):
        weekday_windows[wd] = sorted(weekday_windows[wd], key=lambda x: x[0])

    return {
        'weekday_windows': dict(weekday_windows),
        'exceptions': exceptions,
    }


def load_calendars(con, proj_id: int) -> dict[int, dict[str, Any]]:
    cur = con.cursor()
    rows = cur.execute(
        '''
        SELECT DISTINCT c.CLNDR_ID, c.CLNDR_DATA
        FROM TASK t
        JOIN CALENDAR c ON c.CLNDR_ID = t.CLNDR_ID
        WHERE t.PROJ_ID = ?
          AND t.CLNDR_ID IS NOT NULL
        ''',
        (proj_id,),
    ).fetchall()
    calendars: dict[int, dict[str, Any]] = {}
    for row in rows:
        calendars[int(row['CLNDR_ID'])] = parse_calendar_text(row['CLNDR_DATA'])
    return calendars


def _overlap_hours(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> float:
    start = max(a_start, b_start)
    end = min(a_end, b_end)
    if end <= start:
        return 0.0
    return (end - start).total_seconds() / 3600.0


def spread_calendar(start_dt: datetime | None, end_dt: datetime | None, qty: float, calendar: dict[str, Any] | None, bucket: dict[date, float]) -> None:
    if not start_dt or not end_dt or end_dt < start_dt or qty <= 0:
        return
    if not calendar:
        spread_lv(start_dt.date(), end_dt.date(), qty, bucket)
        return

    weekday_windows = calendar.get('weekday_windows') or {}
    exceptions = calendar.get('exceptions') or set()
    hours_by_day: dict[date, float] = {}

    d = start_dt.date()
    while d <= end_dt.date():
        if d not in exceptions:
            windows = weekday_windows.get(d.weekday(), [])
            hours = 0.0
            for win_start, win_end in windows:
                hours += _overlap_hours(start_dt, end_dt, combine_dt(d, win_start), combine_dt(d, win_end))
            if hours > 0:
                hours_by_day[d] = hours
        d += timedelta(days=1)

    total_hours = sum(hours_by_day.values())
    if total_hours <= 0:
        spread_lv(start_dt.date(), end_dt.date(), qty, bucket)
        return

    for day, hours in sorted(hours_by_day.items()):
        mon = day - timedelta(days=day.weekday())
        bucket[mon] = bucket.get(mon, 0.0) + (qty * hours / total_hours)


def load(args) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'mode': args.mode,
        'cutoff': datetime.strptime(args.cutoff, '%Y-%m-%d').replace(hour=23, minute=59, second=59),
        'base_xer': Path(args.base_xer) if args.base_xer else None,
        'upd_xer': Path(args.upd_xer) if args.upd_xer else None,
        'db': Path(args.db) if args.db else None,
        'proj_id': args.proj_id,
        'base_source': None,
    }

    if payload['db'] and payload['proj_id'] is not None:
        con = open_db(payload['db'])
        try:
            cur = con.cursor()
            rows = cur.execute(
                '''
                SELECT tr.*, t.CLNDR_ID AS TASK_CLNDR_ID,
                       t.EARLY_START_DATE AS TASK_EARLY_START_DATE,
                       t.EARLY_END_DATE AS TASK_EARLY_END_DATE,
                       t.REMAIN_WORK_QTY AS TASK_REMAIN_WORK_QTY,
                       t.ACT_WORK_QTY AS TASK_ACT_WORK_QTY
                FROM TASKRSRC tr
                LEFT JOIN TASK t
                  ON t.PROJ_ID = tr.PROJ_ID
                 AND t.TASK_ID = tr.TASK_ID
                WHERE tr.PROJ_ID=? AND tr.RSRC_TYPE='RT_Labor'
                ''',
                (payload['proj_id'],),
            ).fetchall()
            payload['base_taskrsrc_rows'] = [
                {k.lower(): v for k, v in dict(r).items()}
                for r in rows
            ]
            task_cols = {str(r['name']).upper() for r in cur.execute('PRAGMA table_info(TASK)').fetchall()}
            if {'TARGET_WORK_QTY', 'ACT_WORK_QTY', 'REMAIN_WORK_QTY', 'CLNDR_ID'}.issubset(task_cols):
                if {'TASK_CODE', 'EARLY_START_DATE', 'EARLY_END_DATE', 'TASK_TYPE'}.issubset(task_cols):
                    task_sql = '''
                    SELECT TASK_ID, TASK_CODE, CLNDR_ID,
                           TARGET_START_DATE, TARGET_END_DATE,
                           ACT_START_DATE, ACT_END_DATE,
                           EARLY_START_DATE, EARLY_END_DATE,
                           TARGET_WORK_QTY, ACT_WORK_QTY, REMAIN_WORK_QTY,
                           TASK_TYPE
                    FROM TASK
                    WHERE PROJ_ID=? AND TASK_TYPE != 'TT_Mile'
                    '''
                else:
                    task_sql = '''
                    SELECT TASK_ID, NULL AS TASK_CODE, CLNDR_ID,
                           TARGET_START_DATE, TARGET_END_DATE,
                           ACT_START_DATE, ACT_END_DATE,
                           NULL AS EARLY_START_DATE, NULL AS EARLY_END_DATE,
                           TARGET_WORK_QTY, ACT_WORK_QTY, REMAIN_WORK_QTY,
                           'TT_Task' AS TASK_TYPE
                    FROM TASK
                    WHERE PROJ_ID=?
                    '''
                task_rows = cur.execute(task_sql, (payload['proj_id'],)).fetchall()
                payload['task_rows'] = [
                    {k.lower(): v for k, v in dict(r).items()}
                    for r in task_rows
                ]
            else:
                payload['task_rows'] = []
            payload['calendars'] = load_calendars(con, payload['proj_id'])
            payload['base_source'] = 'db'
        finally:
            con.close()
    elif payload['base_xer']:
        payload['base_taskrsrc_rows'] = parse_table(payload['base_xer'], 'TASKRSRC')
        payload['base_source'] = 'base_xer'
    else:
        payload['base_taskrsrc_rows'] = []

    payload['upd_taskrsrc_rows'] = parse_table(payload['upd_xer'], 'TASKRSRC') if payload['upd_xer'] else []
    return payload


def _compute_logic(payload: dict[str, Any]) -> dict[str, Any]:
    cutoff: datetime = payload['cutoff']
    pv_week = defaultdict(float)
    ev_week = defaultdict(float)
    re_week = defaultdict(float)

    calendars = payload.get('calendars', {})

    if payload.get('base_source') == 'db':
        taskrsrc_rows = payload.get('base_taskrsrc_rows', [])
        for row in taskrsrc_rows:
            if (row.get('rsrc_type') or '').strip() != 'RT_Labor':
                continue
            clndr_id = row.get('task_clndr_id')
            calendar = calendars.get(int(clndr_id)) if clndr_id not in (None, '') else None

            pv = safe_float(row.get('target_qty'))
            pv_start = safe_dt(row.get('target_start_date'))
            pv_end = safe_dt(row.get('target_end_date'))
            if pv > 0 and pv_start and pv_end:
                spread_calendar(pv_start, pv_end, pv, calendar, pv_week)

            ev = safe_float(row.get('act_reg_qty')) + safe_float(row.get('act_ot_qty'))
            if ev <= 0:
                ev = safe_float(row.get('task_act_work_qty'))
            ev_start = safe_dt(row.get('act_start_date'))
            ev_end_raw = safe_dt(row.get('act_end_date'))
            if ev > 0 and ev_start and ev_start <= cutoff:
                ev_end = ev_end_raw if (ev_end_raw and ev_end_raw <= cutoff) else cutoff
                if ev_end >= ev_start:
                    spread_calendar(ev_start, ev_end, ev, calendar, ev_week)

            remain = safe_float(row.get('remain_qty'))
            if remain <= 0:
                remain = safe_float(row.get('task_remain_work_qty'))
            if remain > 0:
                remain_start = cutoff + timedelta(seconds=1)
                early_start = safe_dt(row.get('task_early_start_date'))
                target_start = safe_dt(row.get('target_start_date'))
                for candidate in (early_start, target_start):
                    if candidate and candidate > remain_start:
                        remain_start = candidate
                remain_end = (
                    safe_dt(row.get('task_early_end_date'))
                    or safe_dt(row.get('reend_date'))
                    or safe_dt(row.get('target_end_date'))
                )
                if remain_end and remain_end > cutoff and remain_end >= remain_start:
                    spread_calendar(remain_start, remain_end, remain, calendar, re_week)
    else:
        for row in payload['base_taskrsrc_rows']:
            if (row.get('rsrc_type') or '').strip() != 'RT_Labor':
                continue
            hh = safe_float(row.get('target_qty'))
            ts = safe_dt(row.get('target_start_date'))
            te = safe_dt(row.get('target_end_date'))
            if hh <= 0 or not ts or not te:
                continue
            spread_lv(ts.date(), te.date(), hh, pv_week)

        for row in payload['upd_taskrsrc_rows']:
            if (row.get('rsrc_type') or '').strip() != 'RT_Labor':
                continue
            ev = safe_float(row.get('act_reg_qty')) + safe_float(row.get('act_ot_qty'))
            a_s = safe_dt(row.get('act_start_date'))
            a_e = safe_dt(row.get('act_end_date'))
            if ev > 0 and a_s and a_s <= cutoff:
                end = a_e if (a_e and a_e <= cutoff) else cutoff
                spread_lv(a_s.date(), end.date(), ev, ev_week)
            remain = safe_float(row.get('remain_qty'))
            remain_end = safe_dt(row.get('remain_early_end_date')) or safe_dt(row.get('target_end_date'))
            if remain > 0 and remain_end and remain_end > cutoff:
                start = cutoff + timedelta(seconds=1)
                spread_lv(start.date(), remain_end.date(), remain, re_week)

    weeks = sorted(set(pv_week) | set(ev_week) | set(re_week))
    bac_total = round(sum(safe_float(r.get('target_qty')) for r in payload['base_taskrsrc_rows'] if (r.get('rsrc_type') or '').strip() == 'RT_Labor'), 4)
    rows: list[dict[str, Any]] = []
    pv_cum = 0.0
    ev_cum = 0.0
    re_cum = 0.0
    for mon in weeks:
        pvw = round(float(pv_week.get(mon, 0.0)), 4)
        evw = round(float(ev_week.get(mon, 0.0)), 4)
        rew = round(float(re_week.get(mon, 0.0)), 4)
        pv_cum = round(pv_cum + pvw, 4)
        ev_cum = round(ev_cum + evw, 4)
        re_cum = round(re_cum + rew, 4)
        sv = round(ev_cum - pv_cum, 4)
        spi = round((ev_cum / pv_cum), 6) if pv_cum else None
        forecast_cum = round(ev_cum + re_cum, 4)
        rows.append({
            'week': week_label(mon),
            'pv_week': pvw,
            'pv_cum': pv_cum,
            'pv_pct': round(pv_cum / bac_total * 100, 2) if bac_total else None,
            'ev_cum': ev_cum,
            'ev_pct': round(ev_cum / bac_total * 100, 2) if bac_total else None,
            'sv': sv,
            'spi': spi,
            'forecast_cum': forecast_cum,
            'forecast_pct': round(forecast_cum / bac_total * 100, 2) if bac_total else None,
            'ev_week': evw,
            're_week': rew,
            're_cum': re_cum,
        })

    source_note = 'DB SQLite primaria con calendario real CLNDR_DATA' if payload.get('base_source') == 'db' else 'XER fallback L-V simple'
    return {
        'mode': 'logic',
        'stub': False,
        'note': f"Modo logic calculado con un solo motor temporal para PV, EV y Remaining Early. Fuente base: {source_note}.",
        'rows': rows,
        'bac': round(sum(float(r['pv_week']) for r in rows), 4),
    }


def compute(payload: dict[str, Any]) -> dict[str, Any]:
    if payload['mode'] == 'p6_visual':
        return {
            'mode': 'p6_visual',
            'stub': True,
            'note': 'Modo p6_visual aÃºn no implementado; interfaz reservada y salida estable habilitada.',
            'rows': [],
        }
    return _compute_logic(payload)


def compare(result: dict[str, Any]) -> dict[str, Any]:
    rows = result.get('rows', [])
    last = rows[-1] if rows else {}
    return {
        'mode': result.get('mode'),
        'stub': result.get('stub', False),
        'note': result.get('note', ''),
        'row_count': len(rows),
        'columns': FIXED_COLUMNS,
        'rows': rows,
        'bac': result.get('bac'),
        'pv': last.get('pv_cum', 0.0),
        'ev': last.get('ev_cum', 0.0),
        'sv': last.get('sv'),
        'spi': last.get('spi'),
        'cpi': None,
        'eac': None,
    }


def export(report: dict[str, Any], args) -> Path:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    ext = args.format
    out_path = out_dir / f'pv_engine_{args.mode}_{stamp}.{ext}'

    if ext == 'csv':
        with out_path.open('w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=FIXED_COLUMNS)
            w.writeheader()
            for row in report['rows']:
                w.writerow(row)
    elif ext == 'json':
        with out_path.open('w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    elif ext == 'md':
        with out_path.open('w', encoding='utf-8') as f:
            f.write(f"# PV Engine Report\n\n")
            f.write(f"- mode: `{report['mode']}`\n")
            f.write(f"- stub: `{report['stub']}`\n")
            f.write(f"- row_count: `{report['row_count']}`\n")
            f.write(f"- note: {report['note']}\n\n")
            f.write('| ' + ' | '.join(FIXED_COLUMNS) + ' |\n')
            f.write('|' + '|'.join(['---'] * len(FIXED_COLUMNS)) + '|\n')
            for row in report['rows']:
                vals = [row.get(c, '') for c in FIXED_COLUMNS]
                f.write('| ' + ' | '.join('' if v is None else str(v) for v in vals) + ' |\n')
    else:
        raise SystemExit(f'Formato no soportado: {ext}')
    return out_path


def parse_args():
    ap = argparse.ArgumentParser(
        description='PV engine dual logic / p6_visual',
        epilog='Ruta principal documentada: --db + --proj-id. --base-xer queda como fallback de interoperabilidad cuando no hay acceso a DB.',
    )
    ap.add_argument('--base-xer', help='Fuente baseline secundaria/fallback en XER cuando no hay acceso a DB.')
    ap.add_argument('--upd-xer', help='XER actualizado opcional para EV u operaciones de interoperabilidad.')
    ap.add_argument('--db', help='Fuente primaria: ruta a DB SQLite de P6.')
    ap.add_argument('--proj-id', type=int, help='PROJ_ID en la DB SQLite primaria.')
    ap.add_argument('--cutoff', required=True, help='YYYY-MM-DD')
    ap.add_argument('--mode', choices=['logic', 'p6_visual'], required=True)
    ap.add_argument('--out-dir', default='projects/P6-Standalone-Automation/data')
    ap.add_argument('--format', choices=['csv', 'json', 'md'], default='csv')
    ap.add_argument('--report', choices=['html', 'md', 'xlsx'], help='Render opcional de reporte final unificado despuÃ©s del export base.')
    args = ap.parse_args()
    if not ((args.db and args.proj_id is not None) or args.base_xer):
        ap.error('Debes indicar la fuente primaria --db + --proj-id, o bien --base-xer como fallback si no hay acceso a DB.')
    return args


def main():
    args = parse_args()
    payload = load(args)
    computed = compute(payload)
    report = compare(computed)
    out_path = export(report, args)
    report_out = None
    if args.report:
        meta = {
            'project_name': f"P6 Standalone - {args.proj_id}" if args.proj_id is not None else 'P6 Standalone Report',
            'proj_id': args.proj_id,
        }
        report_out = generate_report(report, args.out_dir, args.report, meta)
    print(f"MODE={report['mode']}")
    print(f"STUB={report['stub']}")
    print(f"ROW_COUNT={report['row_count']}")
    print(f"OUT={out_path}")
    if report_out:
        print(f"REPORT_OUT={report_out}")


if __name__ == '__main__':
    main()
