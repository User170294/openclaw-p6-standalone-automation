from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Font, PatternFill

FIXED_COLUMNS = ['week', 'pv_week', 'pv_cum', 'ev_cum', 'sv', 'spi']


def _safe_num(value: Any) -> float | None:
    if value is None or value == '':
        return None
    try:
        return float(value)
    except Exception:
        return None


def enrich_report(report: dict[str, Any]) -> dict[str, Any]:
    rows = report.get('rows', [])
    last = rows[-1] if rows else {}
    bac = _safe_num(report.get('bac'))
    if bac is None:
        bac = sum(float(row.get('pv_week') or 0.0) for row in rows)
    pv = _safe_num(last.get('pv_cum')) or 0.0
    ev = _safe_num(last.get('ev_cum')) or 0.0
    sv = _safe_num(last.get('sv'))
    spi = _safe_num(last.get('spi'))
    cpi = _safe_num(report.get('cpi'))
    eac = _safe_num(report.get('eac'))
    enriched = dict(report)
    enriched['bac'] = round(bac, 4)
    enriched['kpis'] = {
        'bac': round(bac, 4),
        'pv': round(pv, 4),
        'ev': round(ev, 4),
        'sv': round(sv, 4) if sv is not None else None,
        'spi': round(spi, 6) if spi is not None else None,
        'cpi': round(cpi, 6) if cpi is not None else None,
        'eac': round(eac, 4) if eac is not None else None,
    }
    return enriched


def _fmt_num(value: Any, decimals: int = 4) -> str:
    if value is None or value == '':
        return 'N/A'
    try:
        return f'{float(value):,.{decimals}f}'
    except Exception:
        return str(value)


def _report_stem(report: dict[str, Any], meta: dict[str, Any] | None) -> str:
    mode = report.get('mode', 'logic')
    proj = (meta or {}).get('project_name') or (meta or {}).get('proj_id') or 'report'
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    proj_txt = str(proj).replace(' ', '_')
    return f'report_{proj_txt}_{mode}_{stamp}'


def _build_chart_points(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ''
    labels = [row.get('week', '') for row in rows]
    pv = [float(row.get('pv_cum') or 0.0) for row in rows]
    ev = [float(row.get('ev_cum') or 0.0) for row in rows]
    max_y = max(pv + ev + [1.0])
    points = []
    for idx, values in enumerate((pv, ev)):
        path = []
        for i, value in enumerate(values):
            x = 60 + (780 * i / max(1, len(values) - 1))
            y = 280 - (220 * value / max_y)
            path.append(f'{x:.1f},{y:.1f}')
        color = '#00c2ff' if idx == 0 else '#00e5a0'
        points.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{" ".join(path)}" />')
    x_labels = ''.join(
        f'<text x="{60 + (780 * i / max(1, len(labels) - 1)):.1f}" y="320" fill="#9aa4b2" font-size="11" text-anchor="middle">{escape(lbl)}</text>'
        for i, lbl in enumerate(labels)
    )
    return ''.join(points) + x_labels


def render_html(report: dict[str, Any], out_path: Path, meta: dict[str, Any] | None = None) -> Path:
    report = enrich_report(report)
    rows = report.get('rows', [])
    kpis = report['kpis']
    title = (meta or {}).get('project_name') or 'P6 Standalone Report'
    chart = _build_chart_points(rows)
    table_rows = '\n'.join(
        '<tr>' + ''.join(f'<td>{escape(_fmt_num(row.get(col), 6) if col == "spi" else _fmt_num(row.get(col)) if col != "week" else str(row.get(col, "")))}</td>' for col in FIXED_COLUMNS) + '</tr>'
        for row in rows
    )
    html = f"""<!doctype html>
<html lang='es'>
<head>
<meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{escape(str(title))}</title>
<style>
:root {{ --bg:#0d0f12; --panel:#161a20; --line:#232a35; --txt:#e8edf3; --muted:#9aa4b2; --pv:#00c2ff; --ev:#00e5a0; --sv:#ff4d6a; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--txt); font-family:'IBM Plex Sans',Arial,sans-serif; }}
code, table {{ font-family:'IBM Plex Mono',Consolas,monospace; }}
.container {{ max-width:1400px; margin:0 auto; padding:24px; }}
.grid {{ display:grid; grid-template-columns:repeat(6, minmax(0,1fr)); gap:12px; margin:18px 0 24px; }}
.card {{ background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:16px; }}
.card h3 {{ margin:0 0 6px; font-size:12px; color:var(--muted); text-transform:uppercase; letter-spacing:.08em; }}
.card .value {{ font-size:26px; font-weight:700; }}
.panel {{ background:var(--panel); border:1px solid var(--line); border-radius:16px; padding:18px; margin:14px 0; }}
.table-wrap {{ overflow:auto; }}
table {{ width:100%; border-collapse:collapse; }}
th, td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:right; }}
th:first-child, td:first-child {{ text-align:left; }}
th {{ color:var(--muted); font-size:12px; text-transform:uppercase; }}
.header h1 {{ margin:0; font-size:32px; }}
.header p {{ color:var(--muted); margin:8px 0 0; }}
.legend {{ display:flex; gap:16px; color:var(--muted); font-size:13px; margin-top:10px; }}
.legend span::before {{ content:''; display:inline-block; width:12px; height:12px; border-radius:999px; margin-right:8px; vertical-align:-1px; }}
.legend .pv::before {{ background:var(--pv); }}
.legend .ev::before {{ background:var(--ev); }}
@media (max-width:1100px) {{ .grid {{ grid-template-columns:repeat(2, minmax(0,1fr)); }} }}
</style>
</head>
<body>
<div class='container'>
  <div class='header panel'>
    <h1>{escape(str(title))}</h1>
    <p>{escape(str(report.get('note','')))}</p>
  </div>
  <div class='grid'>
    <div class='card'><h3>BAC</h3><div class='value'>{_fmt_num(kpis['bac'])}</div></div>
    <div class='card'><h3>PV</h3><div class='value'>{_fmt_num(kpis['pv'])}</div></div>
    <div class='card'><h3>EV</h3><div class='value'>{_fmt_num(kpis['ev'])}</div></div>
    <div class='card'><h3>SPI</h3><div class='value'>{_fmt_num(kpis['spi'], 6)}</div></div>
    <div class='card'><h3>CPI</h3><div class='value'>{_fmt_num(kpis['cpi'], 6)}</div></div>
    <div class='card'><h3>EAC</h3><div class='value'>{_fmt_num(kpis['eac'])}</div></div>
  </div>
  <div class='panel'>
    <h2>Curva S</h2>
    <svg viewBox='0 0 900 340' width='100%' height='340' role='img' aria-label='Curva S básica'>
      <rect x='0' y='0' width='900' height='340' fill='#161a20'/>
      <line x1='60' y1='280' x2='840' y2='280' stroke='#232a35' stroke-width='1'/>
      <line x1='60' y1='40' x2='60' y2='280' stroke='#232a35' stroke-width='1'/>
      {chart}
    </svg>
    <div class='legend'><span class='pv'>PV acumulado</span><span class='ev'>EV acumulado</span></div>
  </div>
  <div class='panel table-wrap'>
    <h2>Tabla semanal PV/EV/SV/SPI</h2>
    <table>
      <thead><tr>{''.join(f'<th>{escape(col)}</th>' for col in FIXED_COLUMNS)}</tr></thead>
      <tbody>{table_rows}</tbody>
    </table>
  </div>
</div>
</body>
</html>"""
    out_path.write_text(html, encoding='utf-8')
    return out_path


def render_md(report: dict[str, Any], out_path: Path, meta: dict[str, Any] | None = None) -> Path:
    report = enrich_report(report)
    kpis = report['kpis']
    title = (meta or {}).get('project_name') or 'P6 Standalone Report'
    lines = [
        f'# {title}',
        '',
        '## Estado del reporte',
        f"- Modo: `{report.get('mode', '')}`",
        f"- Nota: {report.get('note', '')}",
        '',
        '## KPIs principales',
        f"- BAC: **{_fmt_num(kpis['bac'])}**",
        f"- PV: **{_fmt_num(kpis['pv'])}**",
        f"- EV: **{_fmt_num(kpis['ev'])}**",
        f"- SPI: **{_fmt_num(kpis['spi'], 6)}**",
        f"- CPI: **{_fmt_num(kpis['cpi'], 6)}**",
        f"- EAC: **{_fmt_num(kpis['eac'])}**",
        '',
        '## Tabla semanal',
        '| ' + ' | '.join(FIXED_COLUMNS) + ' |',
        '|' + '|'.join(['---'] * len(FIXED_COLUMNS)) + '|',
    ]
    for row in report.get('rows', []):
        vals = []
        for col in FIXED_COLUMNS:
            value = row.get(col, '')
            vals.append(str(value))
        lines.append('| ' + ' | '.join(vals) + ' |')
    out_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return out_path


def render_xlsx(report: dict[str, Any], out_path: Path, meta: dict[str, Any] | None = None) -> Path:
    report = enrich_report(report)
    wb = Workbook()
    ws = wb.active
    ws.title = 'weekly_data'
    ws.append(FIXED_COLUMNS)
    header_fill = PatternFill(fill_type='solid', fgColor='0D0F12')
    header_font = Font(color='FFFFFF', bold=True)
    for idx, col in enumerate(FIXED_COLUMNS, start=1):
        cell = ws.cell(row=1, column=idx)
        cell.fill = header_fill
        cell.font = header_font
        ws.column_dimensions[chr(64 + idx)].width = 16
    for row in report.get('rows', []):
        ws.append([row.get(col) for col in FIXED_COLUMNS])

    summary = wb.create_sheet('summary_chart')
    summary['A1'] = (meta or {}).get('project_name') or 'P6 Standalone Report'
    summary['A3'] = 'BAC'; summary['B3'] = report['kpis']['bac']
    summary['A4'] = 'PV'; summary['B4'] = report['kpis']['pv']
    summary['A5'] = 'EV'; summary['B5'] = report['kpis']['ev']
    summary['A6'] = 'SPI'; summary['B6'] = report['kpis']['spi']
    summary['A7'] = 'CPI'; summary['B7'] = report['kpis']['cpi']
    summary['A8'] = 'EAC'; summary['B8'] = report['kpis']['eac']

    chart = LineChart()
    chart.title = 'Curva S'
    chart.y_axis.title = 'HH'
    chart.x_axis.title = 'Week'
    data = Reference(ws, min_col=3, max_col=4, min_row=1, max_row=max(2, ws.max_row))
    cats = Reference(ws, min_col=1, min_row=2, max_row=max(2, ws.max_row))
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.height = 10
    chart.width = 18
    summary.add_chart(chart, 'D3')

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return out_path


def generate_report(report: dict[str, Any], out_dir: str | Path, fmt: str, meta: dict[str, Any] | None = None) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'{_report_stem(report, meta)}.{fmt}'
    if fmt == 'html':
        return render_html(report, out_path, meta)
    if fmt == 'md':
        return render_md(report, out_path, meta)
    if fmt == 'xlsx':
        return render_xlsx(report, out_path, meta)
    raise ValueError(f'Formato de reporte no soportado: {fmt}')


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description='Renderiza reportes finales desde el dict/JSON de pv_engine.compare().')
    ap.add_argument('--input-json', required=True)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--format', choices=['html', 'md', 'xlsx'], required=True)
    ap.add_argument('--project-name', default='P6 Standalone Report')
    args = ap.parse_args()

    report = json.loads(Path(args.input_json).read_text(encoding='utf-8'))
    out = generate_report(report, args.out_dir, args.format, {'project_name': args.project_name})
    print(f'OUT={out}')


if __name__ == '__main__':
    main()
