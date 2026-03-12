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
    proj_code = (meta or {}).get('proj_code') or ''
    cutoff = (meta or {}).get('cutoff') or ''
    bac = kpis['bac']
    pv = kpis['pv']
    ev = kpis['ev']
    spi = kpis['spi']
    cpi = kpis['cpi']
    eac = kpis['eac']

    pv_pct = round(pv / bac * 100, 2) if bac else 0
    ev_pct = round(ev / bac * 100, 2) if bac else 0
    sv = round(ev - pv, 2) if ev is not None and pv is not None else None
    spi_class = 'neg' if (spi is not None and spi < 1) else 'pos'
    cpi_class = 'neg' if (cpi is not None and cpi < 1) else 'pos'
    sv_class = 'neg' if (sv is not None and sv < 0) else 'pos'

    weeks_js = str([r.get('week', '') for r in rows])
    pv_cum_js = str([float(r.get('pv_cum') or 0) for r in rows])
    ev_cum_js = str([float(r.get('ev_cum') or 0) for r in rows])
    pv_week_js = str([float(r.get('pv_week') or 0) for r in rows])

    table_rows_html = ''
    for r in rows:
        w = r.get('week', '')
        pvw = _fmt_num(r.get('pv_week'), 1)
        pvc = _fmt_num(r.get('pv_cum'), 1)
        evc = _fmt_num(r.get('ev_cum'), 1)
        svv = r.get('sv')
        spiv = r.get('spi')
        sv_cls = 'val-neg' if (svv is not None and float(svv) < 0) else 'val-pos'
        spi_cls = 'val-neg' if (spiv is not None and float(spiv) < 1) else ''
        sv_str = _fmt_num(svv, 1) if svv is not None else '—'
        spi_str = _fmt_num(spiv, 3) if spiv is not None else '—'
        table_rows_html += f"<tr><td>{escape(w)}</td><td>{pvw}</td><td>{pvc}</td><td>{evc}</td><td class='{sv_cls}'>{sv_str}</td><td class='{spi_cls}'>{spi_str}</td></tr>\n"

    stamp = datetime.now().strftime('%Y-%m-%d %H:%M')

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape(title)}</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root {{
  --bg:#0d0f12; --surface:#13161b; --border:#1e2530; --border2:#2a3340;
  --text:#c8d0db; --muted:#5a6575; --accent:#00c2ff; --green:#00e5a0;
  --red:#ff4d6a; --yellow:#ffc84a; --pv:#3a7bd5; --ev:#00e5a0;
}}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:var(--bg);color:var(--text);font-family:'IBM Plex Sans',sans-serif;font-size:13px;line-height:1.6;}}
header{{border-bottom:1px solid var(--border);padding:24px 40px 20px;display:flex;align-items:flex-end;justify-content:space-between;gap:20px;}}
.header-tag{{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:2px;text-transform:uppercase;color:var(--accent);}}
.header-title{{font-size:22px;font-weight:600;color:#edf2f7;letter-spacing:-0.3px;}}
.header-sub{{font-size:11px;color:var(--muted);font-family:'IBM Plex Mono',monospace;}}
.cutoff-badge{{background:#1a2235;border:1px solid var(--border2);border-radius:4px;padding:6px 14px;font-family:'IBM Plex Mono',monospace;font-size:11px;color:var(--accent);}}
main{{padding:28px 40px;display:flex;flex-direction:column;gap:28px;}}
.kpi-row{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;}}
.kpi{{background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:16px 18px;display:flex;flex-direction:column;gap:6px;position:relative;overflow:hidden;}}
.kpi::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;}}
.kpi.bac::before{{background:var(--muted);}}
.kpi.pv::before{{background:var(--pv);}}
.kpi.ev::before{{background:var(--ev);}}
.kpi.spi::before{{background:var(--red);}}
.kpi.cpi::before{{background:var(--green);}}
.kpi.eac::before{{background:var(--accent);}}
.kpi-label{{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);}}
.kpi-value{{font-family:'IBM Plex Mono',monospace;font-size:22px;font-weight:600;color:#edf2f7;}}
.kpi-sub{{font-size:10px;color:var(--muted);font-family:'IBM Plex Mono',monospace;}}
.badge{{display:inline-flex;align-items:center;font-family:'IBM Plex Mono',monospace;font-size:10px;padding:2px 6px;border-radius:3px;width:fit-content;}}
.badge.neg{{background:rgba(255,77,106,0.12);color:var(--red);}}
.badge.pos{{background:rgba(0,229,160,0.12);color:var(--green);}}
.badge.neu{{background:rgba(0,194,255,0.12);color:var(--accent);}}
.panel{{background:var(--surface);border:1px solid var(--border);border-radius:6px;overflow:hidden;}}
.panel-header{{padding:14px 20px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}}
.panel-title{{font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:1.5px;text-transform:uppercase;color:var(--accent);}}
.panel-meta{{font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--muted);}}
.panel-body{{padding:20px;}}
.panels{{display:grid;grid-template-columns:1fr 1fr;gap:20px;}}
.panel-full{{grid-column:1/-1;}}
canvas{{display:block;width:100%!important;}}
.data-table{{width:100%;border-collapse:collapse;font-family:'IBM Plex Mono',monospace;font-size:11px;}}
.data-table th{{padding:8px 12px;text-align:right;font-size:9px;letter-spacing:1px;text-transform:uppercase;color:var(--muted);border-bottom:1px solid var(--border);}}
.data-table th:first-child{{text-align:left;}}
.data-table td{{padding:7px 12px;text-align:right;border-bottom:1px solid var(--border);color:var(--text);}}
.data-table td:first-child{{text-align:left;color:var(--accent);}}
.data-table tr:last-child td{{border-bottom:none;}}
.data-table tr:hover td{{background:rgba(255,255,255,0.02);}}
.val-neg{{color:var(--red)!important;}}
.val-pos{{color:var(--green)!important;}}
.legend{{display:flex;gap:20px;flex-wrap:wrap;}}
.legend-item{{display:flex;align-items:center;gap:6px;font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--muted);}}
.legend-dot{{width:8px;height:8px;border-radius:2px;flex-shrink:0;}}
footer{{border-top:1px solid var(--border);padding:16px 40px;display:flex;justify-content:space-between;}}
.footer-text{{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:1px;color:var(--muted);text-transform:uppercase;}}
</style>
</head>
<body>
<header>
  <div>
    <div class="header-tag">P6 Standalone — Control Semanal</div>
    <div class="header-title">{escape(title)}</div>
    <div class="header-sub">{escape(proj_code)}</div>
  </div>
  <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">
    <div class="cutoff-badge">CORTE {escape(cutoff)}</div>
    <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:var(--muted);">Generado: {stamp}</span>
  </div>
</header>
<main>
  <div class="kpi-row">
    <div class="kpi bac">
      <span class="kpi-label">BAC</span>
      <span class="kpi-value">{_fmt_num(bac, 0)}</span>
      <span class="kpi-sub">HH · Línea base</span>
      <span class="badge neu">100%</span>
    </div>
    <div class="kpi pv">
      <span class="kpi-label">PV · Planificado</span>
      <span class="kpi-value">{_fmt_num(pv, 0)}</span>
      <span class="kpi-sub">HH acumuladas</span>
      <span class="badge neu">{pv_pct}%</span>
    </div>
    <div class="kpi ev">
      <span class="kpi-label">EV · Ganado</span>
      <span class="kpi-value">{_fmt_num(ev, 0)}</span>
      <span class="kpi-sub">HH ganadas</span>
      <span class="badge {ev_pct < pv_pct and 'neg' or 'pos'}">{ev_pct}%</span>
    </div>
    <div class="kpi spi">
      <span class="kpi-label">SPI</span>
      <span class="kpi-value">{_fmt_num(spi, 3) if spi is not None else 'N/A'}</span>
      <span class="kpi-sub">EV / PV</span>
      <span class="badge {spi_class}">{_fmt_num(sv, 0) if sv is not None else ''} HH</span>
    </div>
    <div class="kpi cpi">
      <span class="kpi-label">CPI</span>
      <span class="kpi-value">{_fmt_num(cpi, 3) if cpi is not None else 'N/A'}</span>
      <span class="kpi-sub">EV / AC</span>
      <span class="badge {cpi_class}">{'En costo' if cpi is not None and cpi >= 1 else 'Sobre costo'}</span>
    </div>
    <div class="kpi eac">
      <span class="kpi-label">EAC</span>
      <span class="kpi-value">{_fmt_num(eac, 0) if eac is not None else _fmt_num(bac, 0)}</span>
      <span class="kpi-sub">HH · Estimado final</span>
      <span class="badge neu">Forecast</span>
    </div>
  </div>

  <div class="panels">
    <div class="panel panel-full">
      <div class="panel-header">
        <span class="panel-title">Curva S — Avance Acumulado HH</span>
        <div class="legend">
          <div class="legend-item"><div class="legend-dot" style="background:var(--pv)"></div>PV Baseline</div>
          <div class="legend-item"><div class="legend-dot" style="background:var(--ev)"></div>EV Real</div>
        </div>
      </div>
      <div class="panel-body"><canvas id="curvaS" height="220"></canvas></div>
    </div>
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">PV Semanal — Distribución HH</span>
        <span class="panel-meta">L-V · ISO</span>
      </div>
      <div class="panel-body"><canvas id="pvSemanal" height="220"></canvas></div>
    </div>
    <div class="panel">
      <div class="panel-header">
        <span class="panel-title">Schedule Variance (SV)</span>
        <span class="panel-meta">EV − PV por semana</span>
      </div>
      <div class="panel-body"><canvas id="svChart" height="220"></canvas></div>
    </div>
  </div>

  <div class="panel">
    <div class="panel-header">
      <span class="panel-title">Detalle Semanal PV / EV / SV / SPI</span>
      <span class="panel-meta">Fuente: TASKRSRC · RT_Labor</span>
    </div>
    <div class="panel-body" style="padding:0">
      <table class="data-table">
        <thead><tr><th>Semana</th><th>PV Semana</th><th>PV Acum.</th><th>EV Acum.</th><th>SV (HH)</th><th>SPI</th></tr></thead>
        <tbody>{table_rows_html}</tbody>
      </table>
    </div>
  </div>
</main>
<footer>
  <span class="footer-text">P6-Standalone-Automation · OpenClaw</span>
  <span class="footer-text">Generado: {stamp}</span>
</footer>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>
const weeks={weeks_js};
const pvCum={pv_cum_js};
const evCum={ev_cum_js};
const pvWeek={pv_week_js};
const svData=pvCum.map((p,i)=>evCum[i]-p);
Chart.defaults.color='#5a6575';
Chart.defaults.borderColor='#1e2530';
Chart.defaults.font.family="'IBM Plex Mono',monospace";
Chart.defaults.font.size=10;
const grid={{color:'rgba(255,255,255,0.04)',tickColor:'transparent'}};
const ticks={{color:'#5a6575',font:{{size:9}}}};
new Chart(document.getElementById('curvaS'),{{type:'line',data:{{labels:weeks,datasets:[
  {{label:'PV',data:pvCum,borderColor:'#3a7bd5',backgroundColor:'rgba(58,123,213,0.08)',borderWidth:2,pointRadius:3,tension:0.3,fill:true}},
  {{label:'EV',data:evCum,borderColor:'#00e5a0',backgroundColor:'rgba(0,229,160,0.1)',borderWidth:2.5,pointRadius:3,tension:0.3,fill:false}}
]}},options:{{responsive:true,maintainAspectRatio:false,interaction:{{mode:'index',intersect:false}},plugins:{{legend:{{display:false}},tooltip:{{backgroundColor:'#13161b',borderColor:'#2a3340',borderWidth:1,titleColor:'#00c2ff',bodyColor:'#c8d0db',padding:10}}}},scales:{{x:{{grid:grid,ticks:ticks}},y:{{grid:grid,ticks:{{...ticks,callback:v=>v.toLocaleString()}}}}}}}}}}); 
new Chart(document.getElementById('pvSemanal'),{{type:'bar',data:{{labels:weeks,datasets:[{{label:'PV Semanal',data:pvWeek,backgroundColor:'rgba(58,123,213,0.5)',borderColor:'#3a7bd5',borderWidth:1,borderRadius:3}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}},tooltip:{{backgroundColor:'#13161b',borderColor:'#2a3340',borderWidth:1,titleColor:'#00c2ff',bodyColor:'#c8d0db',padding:10}}}},scales:{{x:{{grid:grid,ticks:ticks}},y:{{grid:grid,ticks:{{...ticks,callback:v=>v.toLocaleString()}}}}}}}}}}); 
new Chart(document.getElementById('svChart'),{{type:'bar',data:{{labels:weeks,datasets:[{{label:'SV',data:svData,backgroundColor:svData.map(v=>v<0?'rgba(255,77,106,0.5)':'rgba(0,229,160,0.5)'),borderColor:svData.map(v=>v<0?'#ff4d6a':'#00e5a0'),borderWidth:1,borderRadius:3}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}},tooltip:{{backgroundColor:'#13161b',borderColor:'#2a3340',borderWidth:1,titleColor:'#00c2ff',bodyColor:'#c8d0db',padding:10}}}},scales:{{x:{{grid:grid,ticks:ticks}},y:{{grid:grid,ticks:{{...ticks,callback:v=>v.toLocaleString()}}}}}}}}}}); 
</script>
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
