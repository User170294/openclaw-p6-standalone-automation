import argparse
import sqlite3
from pathlib import Path
from datetime import datetime


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', required=True)
    ap.add_argument('--proj-id', type=int, required=True)
    ap.add_argument('--out-dir', default='projects/P6-Standalone-Automation/data')
    args = ap.parse_args()

    con = sqlite3.connect(Path(args.db))
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    proj = cur.execute('SELECT PROJ_ID, PROJ_SHORT_NAME FROM PROJECT WHERE PROJ_ID=?', (args.proj_id,)).fetchone()
    if not proj:
        raise SystemExit('PROJECT_NOT_FOUND')

    rows = cur.execute(
        'SELECT WBS_ID, PARENT_WBS_ID, WBS_SHORT_NAME, WBS_NAME, SEQ_NUM FROM PROJWBS WHERE PROJ_ID=? ORDER BY SEQ_NUM, WBS_ID',
        (args.proj_id,)
    ).fetchall()

    by_parent = {}
    for r in rows:
        by_parent.setdefault(r['PARENT_WBS_ID'], []).append(r)

    def walk(parent_id, depth, out_lines):
        for n in by_parent.get(parent_id, []):
            indent = '  ' * depth
            short = n['WBS_SHORT_NAME'] or ''
            name = n['WBS_NAME'] or ''
            out_lines.append(f"{indent}- **{short}** — {name}  _(WBS_ID: {n['WBS_ID']})_")
            walk(n['WBS_ID'], depth + 1, out_lines)

    out = []
    out.append(f"# Estructura WBS - Proyecto {proj['PROJ_SHORT_NAME']} ({proj['PROJ_ID']})")
    out.append('')
    out.append(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    out.append('')

    ids = {r['WBS_ID'] for r in rows}
    roots = [
        r for r in rows
        if r['PARENT_WBS_ID'] is None
        or r['PARENT_WBS_ID'] not in ids
        or r['PARENT_WBS_ID'] == r['WBS_ID']
    ]

    if not roots:
        out.append('_No se encontró estructura WBS._')
    else:
        for root in roots:
            out.append(f"- **{root['WBS_SHORT_NAME'] or ''}** — {root['WBS_NAME'] or ''}  _(WBS_ID: {root['WBS_ID']})_")
            walk(root['WBS_ID'], 1, out)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"wbs_{proj['PROJ_ID']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    path.write_text('\n'.join(out), encoding='utf-8')
    print(path)


if __name__ == '__main__':
    main()
