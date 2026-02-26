import argparse
import sqlite3
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--db', required=True)
ap.add_argument('--proj-id', type=int, required=True)
ap.add_argument('--level', type=int, required=True)
args = ap.parse_args()

con = sqlite3.connect(Path(args.db))
con.row_factory = sqlite3.Row
cur = con.cursor()

rows = cur.execute('SELECT WBS_ID, PARENT_WBS_ID, WBS_SHORT_NAME, WBS_NAME FROM PROJWBS WHERE PROJ_ID=?', (args.proj_id,)).fetchall()
by_id = {r['WBS_ID']: r for r in rows}

# roots: parent null or parent outside project
roots = [r for r in rows if r['PARENT_WBS_ID'] is None or r['PARENT_WBS_ID'] not in by_id]

levels = {}

def dfs(node, lvl):
    levels[node['WBS_ID']] = lvl
    children = [r for r in rows if r['PARENT_WBS_ID'] == node['WBS_ID']]
    for c in children:
        dfs(c, lvl+1)

for root in roots:
    dfs(root, 1)

target = [r for r in rows if levels.get(r['WBS_ID']) == args.level]
print(f'COUNT={len(target)}')
for r in sorted(target, key=lambda x: (x['WBS_SHORT_NAME'] or '', x['WBS_ID'])):
    print(f"{r['WBS_ID']}|{r['WBS_SHORT_NAME'] or ''}|{r['WBS_NAME'] or ''}")
