from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any
import sys

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from p6_utils import open_db


DEFAULT_WEEK0 = date(2026, 2, 16)  # ancla vigente OT-1844 para labels W##
FIXED_COLUMNS = ['week', 'pv_week', 'pv_cum', 'ev_cum', 'sv', 'spi']


def week_label(mon: date, anchor: date = DEFAULT_WEEK0) -> str:
    delta = (mon - anchor).days
    if delta < 0:
        iy, iw, _ = mon.isocalendar()
        return f'ISO{iy}-W{iw:02d}'
    return f'W{8 + delta // 7:02d}'


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


def load(args) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'mode': args.mode,
        'cutoff': datetime.strptime(args.cutoff, '%Y-%m-%d').replace(hour=23, minute=59, second=59),
        'base_xer': Path(args.base_xer) if args.base_xer else None,
        'upd_xer': Path(args.upd_xer) if args.upd_xer else None,
        'db': Path(args.db) if args.db else None,
        'proj_id': args.proj_id,
    }

    if payload['base_xer']:
        payload['base_taskrsrc_rows'] = parse_table(payload['base_xer'], 'TASKRSRC')
    elif payload['db'] and payload['proj_id'] is not None:
        con = open_db(payload['db'])
        try:
            cur = con.cursor()
            rows = cur.execute(
                "SELECT * FROM TASKRSRC WHERE PROJ_ID=? AND RSRC_TYPE='RT_Labor'",
                (payload['proj_id'],),
            ).fetchall()
            payload['base_taskrsrc_rows'] = [dict(r) for r in rows]
        finally:
            con.close()
    else:
        payload['base_taskrsrc_rows'] = []

    payload['upd_taskrsrc_rows'] = parse_table(payload['upd_xer'], 'TASKRSRC') if payload['upd_xer'] else []
    return payload


def _compute_logic(payload: dict[str, Any]) -> dict[str, Any]:
    cutoff: datetime = payload['cutoff']
    pv_week = defaultdict(float)
    ev_week = defaultdict(float)

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
        if ev <= 0 or not a_s or a_s > cutoff:
            continue
        end = a_e if (a_e and a_e <= cutoff) else cutoff
        spread_lv(a_s.date(), end.date(), ev, ev_week)

    weeks = sorted(set(pv_week) | set(ev_week))
    rows: list[dict[str, Any]] = []
    pv_cum = 0.0
    ev_cum = 0.0
    for mon in weeks:
        pvw = round(float(pv_week.get(mon, 0.0)), 4)
        pv_cum = round(pv_cum + pvw, 4)
        ev_cum = round(ev_cum + float(ev_week.get(mon, 0.0)), 4)
        sv = round(ev_cum - pv_cum, 4)
        spi = round((ev_cum / pv_cum), 6) if pv_cum else None
        rows.append({
            'week': week_label(mon),
            'pv_week': pvw,
            'pv_cum': pv_cum,
            'ev_cum': ev_cum,
            'sv': sv,
            'spi': spi,
        })

    return {
        'mode': 'logic',
        'stub': False,
        'note': 'Modo logic calculado desde TASKRSRC.target_qty filtrado por RT_Labor y bucket semanal por lunes.',
        'rows': rows,
        'bac': round(sum(float(r['pv_week']) for r in rows), 4),
    }


def compute(payload: dict[str, Any]) -> dict[str, Any]:
    if payload['mode'] == 'p6_visual':
        return {
            'mode': 'p6_visual',
            'stub': True,
            'note': 'Modo p6_visual aún no implementado; interfaz reservada y salida estable habilitada.',
            'rows': [],
        }
    return _compute_logic(payload)


def compare(result: dict[str, Any]) -> dict[str, Any]:
    rows = result.get('rows', [])
    return {
        'mode': result.get('mode'),
        'stub': result.get('stub', False),
        'note': result.get('note', ''),
        'row_count': len(rows),
        'columns': FIXED_COLUMNS,
        'rows': rows,
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
    ap = argparse.ArgumentParser(description='PV engine dual logic / p6_visual')
    ap.add_argument('--base-xer')
    ap.add_argument('--upd-xer')
    ap.add_argument('--db')
    ap.add_argument('--proj-id', type=int)
    ap.add_argument('--cutoff', required=True, help='YYYY-MM-DD')
    ap.add_argument('--mode', choices=['logic', 'p6_visual'], required=True)
    ap.add_argument('--out-dir', default='projects/P6-Standalone-Automation/data')
    ap.add_argument('--format', choices=['csv', 'json', 'md'], default='csv')
    return ap.parse_args()


def main():
    args = parse_args()
    payload = load(args)
    computed = compute(payload)
    report = compare(computed)
    out_path = export(report, args)
    print(f"MODE={report['mode']}")
    print(f"STUB={report['stub']}")
    print(f"ROW_COUNT={report['row_count']}")
    print(f"OUT={out_path}")


if __name__ == '__main__':
    main()
