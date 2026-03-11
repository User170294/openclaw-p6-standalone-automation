import sqlite3
from collections import defaultdict

DB = r"C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db"

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

rows = cur.execute(
    """
    SELECT WBS_ID, PARENT_WBS_ID, COALESCE(WBS_SHORT_NAME,'') AS SHORT, COALESCE(WBS_NAME,'') AS NAME,
           COALESCE(PROJ_NODE_FLAG,'') AS PROJ_NODE_FLAG, PROJ_ID
    FROM PROJWBS
    ORDER BY WBS_ID
    """
).fetchall()

by_parent = defaultdict(list)
by_id = {}
for r in rows:
    by_parent[r['PARENT_WBS_ID']].append(r)
    by_id[r['WBS_ID']] = r

roots = by_parent[None]

print(f"DB={DB}")
print(f"ROOTS={len(roots)}")


def node_type(r):
    return "PROJ" if (r['PROJ_NODE_FLAG'] == 'Y') else "EPS"


def walk(node, depth=0):
    indent = "  " * depth
    t = node_type(node)
    print(f"{indent}- [{t}] {node['WBS_ID']} | {node['SHORT']} | {node['NAME']}")
    children = by_parent.get(node['WBS_ID'], [])
    for c in children:
        walk(c, depth + 1)

for root in roots:
    walk(root, 0)

# EPS summary
all_eps = [r for r in rows if node_type(r) == 'EPS']
print(f"EPS_TOTAL={len(all_eps)}")
for e in all_eps:
    children = by_parent.get(e['WBS_ID'], [])
    eps_children = sum(1 for c in children if node_type(c) == 'EPS')
    proj_children = sum(1 for c in children if node_type(c) == 'PROJ')
    print(f"EPS|{e['WBS_ID']}|{e['SHORT']}|{e['NAME']}|CHILD_EPS={eps_children}|CHILD_PROJ={proj_children}")

con.close()
