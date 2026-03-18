#!/usr/bin/env python3
import argparse
from pathlib import Path
from collections import defaultdict

NUM_FIELDS = [
    'target_qty','remain_qty','act_reg_qty','act_ot_qty','target_cost','act_reg_cost','act_ot_cost','remain_cost',
    'target_qty_per_hr','remain_qty_per_hr','act_this_per_qty','act_this_per_cost','act_work_qty','remain_work_qty','phys_complete_pct'
]


def parse_sections(lines):
    sections = []
    cur = None
    fields = []
    for i, ln in enumerate(lines):
        if ln.startswith('%T\t'):
            cur = ln.split('\t', 1)[1]
            fields = []
        elif ln.startswith('%F\t'):
            fields = ln.split('\t')[1:]
        elif ln.startswith('%R\t') and cur and fields:
            vals = ln.split('\t')[1:]
            if len(vals) < len(fields):
                vals += [''] * (len(fields) - len(vals))
            yield i, cur, fields, vals


def to_float(v):
    try:
        return float(v or 0)
    except Exception:
        return 0.0


def fmt(v):
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return f"{v:.6f}".rstrip('0').rstrip('.')


def main():
    ap = argparse.ArgumentParser(description='Patch XER safely (resource merge and/or progress update).')
    ap.add_argument('--in', dest='inp', required=True)
    ap.add_argument('--out', dest='out', required=True)
    ap.add_argument('--merge-resources', help='Format: OP1,OP2,OP3:OP1,OP2 (drop source, split equally to targets per task).')
    ap.add_argument('--progress-filter', help='Substring filter in TASK.task_name (case-insensitive).')
    ap.add_argument('--progress', type=float, help='Percent complete (0-100).')
    ap.add_argument('--actual-start', help='YYYY-MM-DD HH:MM')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    inp = Path(args.inp)
    out = Path(args.out)
    lines = inp.read_text(encoding='utf-8', errors='ignore').splitlines()

    if not lines or not lines[0].startswith('ERMHDR'):
        raise SystemExit('Invalid XER: missing ERMHDR header')
    if not any(l.strip() == '%E' for l in lines[-5:]):
        raise SystemExit('Invalid XER: missing %E trailer')

    # gather PROJECT/RSRC/TASK/TASKRSRC snapshots
    proj_id = None
    rsrc_by_short = {}
    task_rows = []
    taskrsrc_rows = []

    for ln_idx, tbl, fields, vals in parse_sections(lines):
        m = dict(zip(fields, vals))
        if tbl == 'PROJECT' and proj_id is None:
            proj_id = m.get('proj_id')
        elif tbl == 'RSRC':
            short = (m.get('rsrc_short_name') or '').strip().upper()
            if short:
                rsrc_by_short[short] = m.get('rsrc_id')
        elif tbl == 'TASK':
            task_rows.append((ln_idx, fields, vals, m))
        elif tbl == 'TASKRSRC':
            taskrsrc_rows.append((ln_idx, fields, vals, m))

    if not proj_id:
        raise SystemExit('Could not detect PROJECT.proj_id')

    replacement = {}  # line index -> new line or None(drop)
    report = {
        'merge_changed_tasks': 0,
        'merge_removed_rows': 0,
        'progress_tasks': 0,
        'progress_taskrsrc_rows': 0,
    }

    # 1) optional merge resources
    dropped_resource_ids = set()

    if args.merge_resources:
        spec = args.merge_resources.strip()
        left, right = spec.split(':', 1)
        src_shorts = [x.strip().upper() for x in left.split(',') if x.strip()]
        tgt_shorts = [x.strip().upper() for x in right.split(',') if x.strip()]
        if len(src_shorts) < 2 or len(tgt_shorts) < 1:
            raise SystemExit('Bad --merge-resources format')

        src_ids = [rsrc_by_short.get(s) for s in src_shorts]
        tgt_ids = [rsrc_by_short.get(s) for s in tgt_shorts]
        if any(x is None for x in src_ids + tgt_ids):
            raise SystemExit('Some resource short names were not found in RSRC table')

        drop_id = src_ids[-1]
        dropped_resource_ids.add(drop_id)

        by_task = defaultdict(list)
        for row in taskrsrc_rows:
            ln_idx, fields, vals, m = row
            if m.get('proj_id') != proj_id:
                continue
            by_task[m.get('task_id')].append(row)

        for task_id, grp in by_task.items():
            idx = {f: i for i, f in enumerate(grp[0][1])}
            rows_by_rid = {rid: [] for rid in src_ids}
            for ln_idx, fields, vals, m in grp:
                rid = m.get('rsrc_id')
                if rid in rows_by_rid and m.get('rsrc_type') == 'RT_Labor':
                    rows_by_rid[rid].append((ln_idx, fields, vals, m))

            # require exactly one row for each source in this task
            if not all(len(rows_by_rid[rid]) == 1 for rid in src_ids):
                continue

            drop_row = rows_by_rid[drop_id][0]
            drop_vals = drop_row[2]

            # keep cumulative edits per target line (avoid overwriting previous field changes)
            edited = {}
            for tid in tgt_ids:
                tgt_row = rows_by_rid[tid][0]
                edited[tgt_row[0]] = tgt_row[2][:]

            for fld in NUM_FIELDS:
                if fld in idx:
                    j = idx[fld]
                    add = to_float(drop_vals[j])
                    if add:
                        share = add / len(tgt_ids)
                        for tid in tgt_ids:
                            tgt_row = rows_by_rid[tid][0]
                            ln = tgt_row[0]
                            edited[ln][j] = fmt(to_float(edited[ln][j]) + share)

            for ln, vals_new in edited.items():
                replacement[ln] = '%R\t' + '\t'.join(vals_new)

            replacement[drop_row[0]] = None
            report['merge_changed_tasks'] += 1
            report['merge_removed_rows'] += 1

    # 2) optional progress update by task_name filter
    progress_task_ids = set()
    if args.progress_filter and args.progress is not None and args.actual_start:
        needle = args.progress_filter.lower()
        pct = float(args.progress)

        for ln_idx, fields, vals, m in task_rows:
            if m.get('proj_id') != proj_id:
                continue
            if needle not in (m.get('task_name') or '').lower():
                continue

            idx = {f: i for i, f in enumerate(fields)}
            new_vals = vals[:]
            if 'status_code' in idx:
                new_vals[idx['status_code']] = 'TK_Active'
            if 'phys_complete_pct' in idx:
                new_vals[idx['phys_complete_pct']] = fmt(pct)
            if 'act_start_date' in idx:
                new_vals[idx['act_start_date']] = args.actual_start
            if 'target_work_qty' in idx and 'act_work_qty' in idx and 'remain_work_qty' in idx:
                tw = to_float(new_vals[idx['target_work_qty']])
                act = tw * (pct / 100.0)
                rem = max(0.0, tw - act)
                new_vals[idx['act_work_qty']] = fmt(act)
                new_vals[idx['remain_work_qty']] = fmt(rem)

            replacement[ln_idx] = '%R\t' + '\t'.join(new_vals)
            report['progress_tasks'] += 1
            progress_task_ids.add(m.get('task_id'))

        # TASKRSRC mirror
        for ln_idx, fields, vals, m in taskrsrc_rows:
            if m.get('proj_id') != proj_id or m.get('task_id') not in progress_task_ids:
                continue
            if m.get('rsrc_type') != 'RT_Labor':
                continue
            # if this row was dropped by merge, keep it dropped
            if replacement.get(ln_idx) is None:
                continue
            # don't revive dropped source resources (e.g., OP3)
            if m.get('rsrc_id') in dropped_resource_ids:
                continue
            idx = {f: i for i, f in enumerate(fields)}
            # If merge already updated this line, continue from merged values.
            rep_line = replacement.get(ln_idx)
            if rep_line:
                rep_vals = rep_line.split('\t')[1:]
                rep_vals += [''] * (len(fields) - len(rep_vals))
                new_vals = rep_vals[:len(fields)]
            else:
                new_vals = vals[:]
            if 'target_qty' in idx and 'act_reg_qty' in idx and 'remain_qty' in idx:
                tq = to_float(new_vals[idx['target_qty']])
                act = tq * (pct / 100.0)
                rem = max(0.0, tq - act)
                new_vals[idx['act_reg_qty']] = fmt(act)
                new_vals[idx['remain_qty']] = fmt(rem)
            if 'act_start_date' in idx:
                new_vals[idx['act_start_date']] = args.actual_start
            if 'act_end_date' in idx:
                new_vals[idx['act_end_date']] = ''
            replacement[ln_idx] = '%R\t' + '\t'.join(new_vals)
            report['progress_taskrsrc_rows'] += 1

    # rebuild lines preserving envelope + untouched rows
    new_lines = []
    for i, ln in enumerate(lines):
        if i in replacement:
            rep = replacement[i]
            if rep is None:
                continue
            new_lines.append(rep)
        else:
            new_lines.append(ln)

    # safety checks
    if not new_lines[0].startswith('ERMHDR'):
        raise SystemExit('Patch produced invalid XER: ERMHDR missing')
    if '%E' not in set(x.strip() for x in new_lines[-5:]):
        raise SystemExit('Patch produced invalid XER: %E missing')

    # quick labor target conservation check
    def labor_target_total(src_lines):
        total = 0.0
        cur = None
        fields = []
        for ln in src_lines:
            if ln.startswith('%T\t'):
                cur = ln.split('\t', 1)[1]
                fields = []
            elif ln.startswith('%F\t'):
                fields = ln.split('\t')[1:]
            elif ln.startswith('%R\t') and cur == 'TASKRSRC' and fields:
                vals = ln.split('\t')[1:]
                if len(vals) < len(fields):
                    vals += [''] * (len(fields) - len(vals))
                m = dict(zip(fields, vals))
                if m.get('proj_id') == proj_id and m.get('rsrc_type') == 'RT_Labor':
                    total += to_float(m.get('target_qty'))
        return total

    before_total = labor_target_total(lines)
    after_total = labor_target_total(new_lines)

    print(f"SUMMARY merge_changed_tasks={report['merge_changed_tasks']} merge_removed_rows={report['merge_removed_rows']} progress_tasks={report['progress_tasks']} progress_taskrsrc={report['progress_taskrsrc_rows']}")
    print(f"LABOR_TARGET before={fmt(before_total)} after={fmt(after_total)}")

    if args.dry_run:
        print('DRY_RUN no file written')
        return

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')
    print(f"WROTE {out}")


if __name__ == '__main__':
    main()