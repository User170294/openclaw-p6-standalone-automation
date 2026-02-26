import pandas as pd
import os
from datetime import datetime

base = r"C:\Users\josej\.openclaw\workspace\projects\Bodega-Simtexx\reports"

# tomar consolidado más reciente
candidatos = sorted([f for f in os.listdir(base) if f.startswith('bodega_unificado_') and f.endswith('.csv')])
if not candidatos:
    raise SystemExit('No se encontró bodega_unificado_*.csv')

src = os.path.join(base, candidatos[-1])
df = pd.read_csv(src, encoding='utf-8-sig')

req = ['Cod. Producto', 'Producto', 'Bodega', 'Stock Total', 'Costo Unit.', 'Costo Total', 'Cod. U. Medida']
for c in req:
    if c not in df.columns:
        raise SystemExit(f'Falta columna requerida: {c}')

# normalización
df['Stock Total'] = pd.to_numeric(df['Stock Total'], errors='coerce').fillna(0)
df['Costo Unit.'] = pd.to_numeric(df['Costo Unit.'], errors='coerce').fillna(0)
df['Costo Total'] = pd.to_numeric(df['Costo Total'], errors='coerce').fillna(0)

group_cols = ['Cod. Producto', 'Producto']

# stock por bodega en columnas
pivot_stock = pd.pivot_table(
    df,
    index=group_cols,
    columns='Bodega',
    values='Stock Total',
    aggfunc='sum',
    fill_value=0
).reset_index()
pivot_stock.columns = [str(c) if c in group_cols else f"Stock - {c}" for c in pivot_stock.columns]

# metadatos por producto
meta = df.groupby(group_cols, as_index=False).agg({
    'Cod. U. Medida': lambda s: ' | '.join(sorted({str(x).strip() for x in s.dropna() if str(x).strip() not in ['', 'nan']})),
    'Costo Unit.': 'max',
    'Costo Total': 'sum'
})

out = pivot_stock.merge(meta, on=group_cols, how='left')

# orden columnas
stock_cols = [c for c in out.columns if c.startswith('Stock - ')]
out['Stock Total Consolidado'] = out[stock_cols].sum(axis=1)
final_cols = ['Cod. Producto', 'Producto', 'Cod. U. Medida'] + stock_cols + ['Stock Total Consolidado', 'Costo Unit.', 'Costo Total']
out = out[final_cols]

stamp = datetime.now().strftime('%Y%m%d_%H%M')
out_xlsx = os.path.join(base, f'bodega_stock_enriquecido_{stamp}.xlsx')
out_csv = os.path.join(base, f'bodega_stock_enriquecido_{stamp}.csv')

with pd.ExcelWriter(out_xlsx, engine='openpyxl') as writer:
    out.to_excel(writer, sheet_name='Stock Enriquecido', index=False)

out.to_csv(out_csv, index=False, encoding='utf-8-sig')

print(f'SRC::{src}')
print(f'OK_XLSX::{out_xlsx}')
print(f'OK_CSV::{out_csv}')
print(f'FILAS::{len(out)}')
