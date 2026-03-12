from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_CORE = ROOT / 'scripts' / 'core'
if str(SCRIPTS_CORE) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_CORE))

import report_generator  # noqa: E402


SAMPLE_REPORT = {
    'mode': 'logic',
    'stub': False,
    'note': 'Reporte de prueba para render final.',
    'row_count': 2,
    'columns': ['week', 'pv_week', 'pv_cum', 'ev_cum', 'sv', 'spi'],
    'bac': 300.0,
    'pv': 300.0,
    'ev': 250.0,
    'sv': -50.0,
    'spi': 0.833333,
    'cpi': None,
    'eac': None,
    'rows': [
        {'week': 'W08', 'pv_week': 100.0, 'pv_cum': 100.0, 'ev_cum': 80.0, 'sv': -20.0, 'spi': 0.8},
        {'week': 'W09', 'pv_week': 200.0, 'pv_cum': 300.0, 'ev_cum': 250.0, 'sv': -50.0, 'spi': 0.833333},
    ],
}


def test_render_html_generates_non_empty_file(tmp_path):
    out = report_generator.generate_report(SAMPLE_REPORT, tmp_path, 'html', {'project_name': 'OT-1844'})
    text = out.read_text(encoding='utf-8')
    assert out.exists()
    assert out.stat().st_size > 0
    assert '<table>' in text
    assert 'pv_week' in text
    assert 'Curva S' in text


def test_render_md_generates_non_empty_file(tmp_path):
    out = report_generator.generate_report(SAMPLE_REPORT, tmp_path, 'md', {'project_name': 'OT-1844'})
    text = out.read_text(encoding='utf-8')
    assert out.exists()
    assert out.stat().st_size > 0
    assert '# OT-1844' in text
    assert '| week | pv_week | pv_cum | ev_cum | sv | spi |' in text


def test_render_xlsx_generates_expected_sheets_and_columns(tmp_path):
    out = report_generator.generate_report(SAMPLE_REPORT, tmp_path, 'xlsx', {'project_name': 'OT-1844'})
    assert out.exists()
    assert out.stat().st_size > 0
    wb = load_workbook(out)
    assert 'weekly_data' in wb.sheetnames
    assert 'summary_chart' in wb.sheetnames
    ws = wb['weekly_data']
    headers = [ws.cell(row=1, column=i).value for i in range(1, 7)]
    assert headers == ['week', 'pv_week', 'pv_cum', 'ev_cum', 'sv', 'spi']
