import pandas as pd
import os
from datetime import datetime

base = r"C:\Users\josej\.openclaw\workspace\projects\Bodega-Simtexx\reports"

# Toma el consolidado más reciente
candidatos = [f for f in os.listdir(base) if f.startswith('bodega_unificado_') and f.endswith('.csv')]
if not candidatos:
    raise SystemExit('No se encontró consolidado bodega_unificado_*.csv')

candidatos.sort()
src = os.path.join(base, candidatos[-1])
df = pd.read_csv(src, encoding='utf-8-sig')

# Normalización básica
for c in ['Cod. Producto', 'Producto', 'Bodega', 'Stock Total', 'Disponible']:
    if c not in df.columns:
        raise SystemExit(f'Falta columna requerida: {c}')

for c in ['Stock Total', 'Disponible']:
    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

group_cols = ['Cod. Producto', 'Producto']

pivot_stock = pd.pivot_table(
    df,
    index=group_cols,
    columns='Bodega',
    values='Stock Total',
    aggfunc='sum',
    fill_value=0
).reset_index()

pivot_disp = pd.pivot_table(
    df,
    index=group_cols,
    columns='Bodega',
    values='Disponible',
    aggfunc='sum',
    fill_value=0
).reset_index()

# Renombrar columnas para claridad
pivot_stock.columns = [str(c) if c in group_cols else f"Stock Total - {c}" for c in pivot_stock.columns]
pivot_disp.columns  = [str(c) if c in group_cols else f"Disponible - {c}" for c in pivot_disp.columns]

# Merge en un solo archivo reducido por producto
out = pivot_stock.merge(pivot_disp, on=group_cols, how='outer').fillna(0)

# Total general por producto
stock_cols = [c for c in out.columns if c.startswith('Stock Total - ')]
out['Stock Total Consolidado'] = out[stock_cols].sum(axis=1)

stamp = datetime.now().strftime('%Y%m%d_%H%M')
out_xlsx = os.path.join(base, f'bodega_cantidades_por_bodega_{stamp}.xlsx')
out_csv = os.path.join(base, f'bodega_cantidades_por_bodega_{stamp}.csv')

with pd.ExcelWriter(out_xlsx, engine='openpyxl') as writer:
    out.to_excel(writer, sheet_name='Cantidades por bodega', index=False)

out.to_csv(out_csv, index=False, encoding='utf-8-sig')

print(f'SRC::{src}')
print(f'OK_XLSX::{out_xlsx}')
print(f'OK_CSV::{out_csv}')
print(f'FILAS::{len(out)}')
