import argparse
from pathlib import Path
import sys
from datetime import datetime
import json

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from p6_utils import open_db


def main():
    ap = argparse.ArgumentParser(description='Plan-only clone for P6 Standalone (no changes).')
    ap.add_argument('--db', required=True)
    ap.add_argument('--source-proj-id', type=int, required=True)
    ap.add_argument('--target-short-name', required=True)
    ap.add_argument('--out-dir', default='projects/P6-Standalone-Automation/data')
    args = ap.parse_args()

    db = Path(args.db)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    con = open_db(db)
    cur = con.cursor()

    cur.execute('SELECT PROJ_ID, PROJ_SHORT_NAME, PLAN_START_DATE, PLAN_END_DATE, LAST_SCHEDULE_DATE FROM PROJECT WHERE PROJ_ID=?', (args.source_proj_id,))
    src = cur.fetchone()
    cur.execute("SELECT PROJ_ID, PROJ_SHORT_NAME FROM PROJECT WHERE UPPER(COALESCE(PROJ_SHORT_NAME,'')) = UPPER(?)", (args.target_short_name,))
    tgt = cur.fetchone()

    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    plan = {
        'timestamp': stamp,
        'mode': 'plan',
        'db': str(db),
        'source_project': dict(src) if src else None,
        'target_short_name': args.target_short_name,
        'target_exists': bool(tgt),
        'target_project': dict(tgt) if tgt else None,
        'can_proceed': bool(src) and not bool(tgt),
        'ui_steps': [
            'Open Primavera P6 Professional and switch to Projects view',
            f'Select source project ID {args.source_proj_id}',
            'Copy project (Ctrl+C) and Paste as a new project',
            f'Set new Project ID/Short Name to {args.target_short_name}',
            'Confirm project options (calendars/codes/settings copied)',
            'Run schedule check and save',
            'Capture screenshot evidence and write execution log'
        ],
        'guards': [
            'Abort if source project not found',
            'Abort if target short name already exists',
            'Abort on unexpected modal dialog',
            'No direct DB writes'
        ]
    }

    json_path = out / f'clone_plan_{stamp}.json'
    md_path = out / f'clone_plan_{stamp}.md'
    with json_path.open('w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    with md_path.open('w', encoding='utf-8') as f:
        f.write(f"# Clone Plan (modo plan) - {stamp}\n\n")
        f.write(f"- Source PROJ_ID: `{args.source_proj_id}`\n")
        f.write(f"- Target short name: `{args.target_short_name}`\n")
        f.write(f"- Source existe: `{bool(src)}`\n")
        f.write(f"- Target ya existe: `{bool(tgt)}`\n")
        f.write(f"- Puede proceder: `{bool(src) and not bool(tgt)}`\n\n")
        if src:
            f.write('## Source\n')
            for k in src.keys():
                f.write(f"- {k}: `{src[k]}`\n")
            f.write('\n')
        if tgt:
            f.write('## Target encontrado\n')
            for k in tgt.keys():
                f.write(f"- {k}: `{tgt[k]}`\n")
            f.write('\n')
        f.write('## Pasos UI\n')
        for i, s in enumerate(plan['ui_steps'], start=1):
            f.write(f"{i}. {s}\n")

    print(f'PLAN_JSON={json_path}')
    print(f'PLAN_MD={md_path}')
    print(f"CAN_PROCEED={plan['can_proceed']}")
    con.close()


if __name__ == '__main__':
    main()
