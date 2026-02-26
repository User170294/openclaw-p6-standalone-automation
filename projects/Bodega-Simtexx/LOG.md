# LOG - Bodega Simtexx

## 2026-02-26 13:05 (UTC-3)
- Proyecto creado en workspace.
- Se definió objetivo general: cuadratura de insumos + trazabilidad de entrada/salida.
- Se inicializaron archivos base (README, MEMORY, INDEX).
- Próximo paso: discovery operativo (AS-IS) por bodega.

## 2026-02-26 13:06 (UTC-3)
- Se confirmó carpeta fuente para documentos de ingesta RAG:
  `C:\Users\josej\OneDrive - SIMTEXX SPA\OPERACIONES - Documentos\005_Bodega`
- Verificación rápida: se detectan al menos 3 archivos Excel (stock casa matriz, sucursal la chimba, terreno).

## 2026-02-26 13:08 (UTC-3)
- Se generó primer consolidado único en `projects/Bodega-Simtexx/reports/`:
  - `bodega_unificado_20260226_1308.xlsx`
  - `bodega_unificado_20260226_1308.csv`
- Registros consolidados: 528 filas.
- Observación: `SM_STOCK CASA MATRIZ.xlsx` quedó bloqueado (Permission denied), no entró en este primer corte.

## 2026-02-26 13:11 (UTC-3)
- Se generó vista reducida por producto con cantidades en columnas por bodega:
  - `bodega_cantidades_por_bodega_20260226_1311.xlsx`
  - `bodega_cantidades_por_bodega_20260226_1311.csv`
- Filas resultantes: 313 productos únicos.
- Objetivo: disminuir líneas repetidas y facilitar comparación entre bodegas.

## 2026-02-26 13:14 (UTC-3)
- Se reprocesó consolidado incluyendo `SM_STOCK CASA MATRIZ.xlsx` (archivo antes bloqueado):
  - `bodega_unificado_20260226_1314.xlsx`
  - `bodega_unificado_20260226_1314.csv`
- Registros consolidados: 914 filas.
- Se simplificó informe pivote eliminando `Disponible` por redundancia con `Stock`:
  - `bodega_stock_por_bodega_20260226_1314.xlsx`
  - `bodega_stock_por_bodega_20260226_1314.csv`
- Resultado pivote: 490 productos únicos.

## 2026-02-26 13:24 (UTC-3)
- Se agregaron columnas solicitadas al informe pivote: `Cod. U. Medida`, `Costo Unit.`, `Costo Total`.
- Archivo generado:
  - `bodega_stock_enriquecido_20260226_1324.xlsx`
  - `bodega_stock_enriquecido_20260226_1324.csv`
- Filas resultantes: 482 productos únicos.
- Observación: en esta corrida `TE_TERRENO.xlsx` estaba bloqueado (Permission denied), por lo que no entró en este corte.