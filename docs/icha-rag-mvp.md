# ICHA RAG MVP (local)

Objetivo: consultar datos del Excel ICHA sin cargar el archivo completo al contexto.

## 1) Construir índice

```bash
py -3 scripts/build_icha_index.py --input "C:\Users\josej\Desktop\ICHA (001).xlsx" --out-dir data
```

Genera:
- `data/icha_catalogo_normalizado.jsonl` (registros por fila útil)
- `data/icha_indice.json` (resumen de hojas/familias)

## 2) Consultar índice

Ejemplos:

```bash
py -3 scripts/query_icha.py --q "IN 100" --limit 5
py -3 scripts/query_icha.py --family IN --min-peso 300 --limit 10
py -3 scripts/query_icha.py --q "pandeo" --limit 5
```

## Notas
- El parser es robusto para plantillas con encabezados complejos y celdas combinadas.
- Se guarda trazabilidad: hoja + fila original.
- Se puede extender a PDF y otros catálogos con el mismo patrón.
