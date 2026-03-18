import argparse
import csv
from pathlib import Path


def load_csv(path: Path, week_col: str, value_col: str, cum_col: str | None):
    rows = {}
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            week = (row.get(week_col) or '').strip()
            if not week:
                continue
            value = float((row.get(value_col) or '0').strip() or 0)
            if cum_col:
                cum = float((row.get(cum_col) or '0').strip() or 0)
            else:
                cum = None
            rows[week] = {
                'week': week,
                'value': value,
                'cum': cum,
                'raw': row,
            }
    if cum_col is None:
        running = 0.0
        for week in sorted(rows):
            running += rows[week]['value']
            rows[week]['cum'] = running
    return rows


def fmt_num(v: float) -> str:
    return f'{v:.4f}'


def main():
    ap = argparse.ArgumentParser(description='Compara curva semanal XER vs DB a partir de dos CSV normalizados.')
    ap.add_argument('--xer-csv', required=True, help='CSV semanal proveniente de XER')
    ap.add_argument('--db-csv', required=True, help='CSV semanal proveniente de DB')
    ap.add_argument('--out-csv', required=True, help='Ruta de salida del comparativo')
    ap.add_argument('--week-col', default='week', help='Nombre de la columna de semana en ambos CSV')
    ap.add_argument('--xer-value-col', default='pv', help='Columna semanal del CSV XER')
    ap.add_argument('--db-value-col', default='pv', help='Columna semanal del CSV DB')
    ap.add_argument('--xer-cum-col', default='acum', help='Columna acumulada del CSV XER (vacío para recalcular)')
    ap.add_argument('--db-cum-col', default='acum', help='Columna acumulada del CSV DB (vacío para recalcular)')
    args = ap.parse_args()

    xer_path = Path(args.xer_csv)
    db_path = Path(args.db_csv)
    out_path = Path(args.out_csv)

    xer = load_csv(xer_path, args.week_col, args.xer_value_col, args.xer_cum_col or None)
    db = load_csv(db_path, args.week_col, args.db_value_col, args.db_cum_col or None)

    weeks = sorted(set(xer) | set(db))
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        'week',
        'xer_value',
        'db_value',
        'delta_value',
        'xer_cum',
        'db_cum',
        'delta_cum',
    ]

    max_abs_delta_value = 0.0
    max_abs_delta_cum = 0.0

    with out_path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for week in weeks:
            xv = float(xer.get(week, {}).get('value', 0.0))
            dv = float(db.get(week, {}).get('value', 0.0))
            xc = float(xer.get(week, {}).get('cum', 0.0))
            dc = float(db.get(week, {}).get('cum', 0.0))
            ddv = dv - xv
            ddc = dc - xc
            max_abs_delta_value = max(max_abs_delta_value, abs(ddv))
            max_abs_delta_cum = max(max_abs_delta_cum, abs(ddc))
            writer.writerow(
                {
                    'week': week,
                    'xer_value': fmt_num(xv),
                    'db_value': fmt_num(dv),
                    'delta_value': fmt_num(ddv),
                    'xer_cum': fmt_num(xc),
                    'db_cum': fmt_num(dc),
                    'delta_cum': fmt_num(ddc),
                }
            )

    print(f'XER_ROWS={len(xer)}')
    print(f'DB_ROWS={len(db)}')
    print(f'WEEKS={len(weeks)}')
    print(f'MAX_ABS_DELTA_VALUE={fmt_num(max_abs_delta_value)}')
    print(f'MAX_ABS_DELTA_CUM={fmt_num(max_abs_delta_cum)}')
    print(f'OUT={out_path}')


if __name__ == '__main__':
    main()