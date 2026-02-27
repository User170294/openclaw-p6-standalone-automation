# LOG - P6-Standalone-Automation

## 2026-02-26 14:33 (UTC-3)
- Proyecto inicializado en `projects/P6-Standalone-Automation`.
- Estructura creada: `docs/`, `scripts/`, `data/`.
- Archivos base creados: README.md, MEMORY.md, LOG.md, INDEX.csv.

## 2026-02-26 14:37 (UTC-3)
- Base SQLite confirmada: `C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B - copia.db`.
- Script de inspección creado: `scripts/inspect_sqlite.py`.
- Script piloto de auditoría creado: `scripts/pilot_audit.py`.
- Corrida en dry-run ejecutada.
- Resultados: NO_PREDECESSOR=10837, OVERDUE_MILESTONE=6566.
- Reportes generados en `data/`: `pilot_audit_20260226_143723.csv` y `pilot_audit_20260226_143723.md`.

## 2026-02-27 16:15 (UTC-3)
- Ruta base SQLite actualizada por usuario a: `C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db`.
- Se actualizan scripts base para usar la nueva ruta: `scripts/inspect_sqlite.py` y `scripts/create_project_under_simtexx.py`.

## 2026-02-27 16:32 (UTC-3)
- Eliminado proyecto `PROJ_ID=26196` (`OT 1844_B`) desde SQLite en operación transaccional.
- Respaldo previo generado: `C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.BACKUP_20260227_163242.db`.
- Registros eliminados (principal): PROJECT=1, PROJWBS=44, TASK=165, TASKPRED=181, TASKRSRC=476, REFRDEL=1443.
- Verificación posterior: `PROJECT_LEFT=0`.

## 2026-02-27 17:10 (UTC-3)
- Limpieza masiva de EPS raíz para conservar solo `WBS_ID=151785` (`Simtexx | Maestranza`).
- Respaldo previo generado: `C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.BACKUP_20260227_171013.db`.
- Ejecución transaccional con `scripts/prune_eps_keep_root.py --keep-root 151785 --apply`.
- Eliminados: PROJECT=1103, PROJWBS=54769, TASK=184533, TASKPRED=238938, TASKRSRC=221717.
- Verificación posterior: `ROOTS_LEFT=1` y raíz remanente `151785|Simtexx|Maestranza`.

## 2026-02-27 17:24 (UTC-3)
- Proyecto objetivo: `PROJ_ID=26258` (`OT 1844_B`).
- Recurso original intervenido: `RSRC_ID=9398`.
- Respaldo previo generado: `C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.BACKUP_20260227_172424.db`.
- Script aplicado: `scripts/replace_resource_with_three_ops.py --proj-id 26258 --old-rsrc 9398 --apply`.
- Recursos nuevos creados (RT_Labor): `9570=OP1`, `9571=OP2`, `9572=OP3`.
- Reasignación: 151 asignaciones originales repartidas en 3 por actividad (total nuevas filas TASKRSRC: 453 para OP1/OP2/OP3).
- Conservación HH validada: total `TARGET_QTY` del recurso reemplazado se mantuvo en `7740.0` (2580.0 por cada OP).
- Estado final de recursos del proyecto: OP1, OP2, OP3 + `9399 (Ing. OT 1844)`.
