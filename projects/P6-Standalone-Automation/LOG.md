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

## 2026-02-27 17:40 (UTC-3)
- Ajuste correctivo de distribución temporal en `PROJ_ID=26258` tras detectar desalineación de curva respecto a `26260`.
- Respaldo previo generado: `C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.BACKUP_20260227_174014.db`.
- Script aplicado: `scripts/fix_op_rate_spread.py --proj-id 26258 --op-ids 9570,9571,9572 --apply`.
- Acción: división por 3 de `TARGET_QTY_PER_HR` y `REMAIN_QTY_PER_HR` en 453 asignaciones OP.
- Resultado: `SUM_TQPH` proyecto 26258 quedó en `346.000021` (vs `346.0` en 26260; diferencia mínima por redondeo).

## 2026-02-28 14:06 (UTC-3)
- Ingestado est�ndar de planificaci�n solicitado por usuario:
  C:\Users\josej\OneDrive - SIMTEXX SPA\PO 4519143302 Fabricaci�n Bandejas Agua Lavado Celda_OT 1844 Celdas - Documentos\Planificaci�n\PRACTICE STANDARD FOR SCHEDULING 3ra.pdf.
- Proceso ejecutado: scripts/ingest_project_pdfs.py (fuente staging local en data/ingest_tmp/p6-standalone-automation).
- Resultado ingesti�n: pdf_found=1, pdf_indexed=1, chunks_added=400.
- Archivos actualizados: data/p6-standalone-automation_docs.jsonl, data/p6-standalone-automation_chunks.jsonl, projects/P6-Standalone-Automation/INDEX.csv, projects/P6-Standalone-Automation/docs/summaries/PRACTICE STANDARD FOR SCHEDULING 3ra.md.
- Indexaci�n vectorial ejecutada con scripts/embed_chunks.py.
- Colecci�n ChromaDB: p6_standalone_automation con 400 chunks.

## 2026-03-09 16:10 (UTC-3)
- Se consolida estándar operativo para extracción de PV/EV semanal desde XER (caso OT-1844).
- Regla fijada para PV baseline: `TASKRSRC.target_qty` + filtro `RT_Labor` + prorrateo diario L-V + agregación semana ISO (lunes-domingo).
- Hitos de validación registrados: W08=1134 HH (14.00%), W09=2295 HH (28.33%), W10=3771 HH (46.56%).
- EV al corte W11 validado desde XER actualizado: 3394.8 HH (41.91%).
- Objetivo: reutilizar este método como plantilla en automatizaciones P6 futuras para evitar desalineaciones en reportes.

## 2026-03-09 21:29 (UTC-3)
- Se detecta falla crítica al editar XER por script: archivo generado inválido para import en P6 por pérdida de cabecera `ERMHDR` y cierre `%E`.
- Causa: reconstrucción completa del archivo sin preservar envolvente nativa del XER.
- Acción correctiva: nuevo método de parche por líneas (solo `TASKRSRC`), preservando 100% del resto del archivo.
- Resultado: XER reparado `SPC-Rev.B_Prueba_OP12_FIX2.xer` con import válido esperado, HH totales conservadas (`8100`), OP3 removido y redistribución 50/50 a OP1/OP2.
- Lección obligatoria: en modificaciones XER, nunca reserializar el archivo completo si no es estrictamente necesario; aplicar edición incremental y validar `ERMHDR` + `%E` + totales antes de importar.

## 2026-03-09 23:38 (UTC-3)
- Sesión de depuración profunda del cálculo PV semanal en `OT-1616_0 - B1` usando BD + XER + contraste con Usage Spreadsheet P6.
- Se descartó definitivamente el prorrateo diario plano para casos con inicio/fin intra-día y excepciones de calendario.
- Se validó metodología robusta: distribución por horas efectivas de solape sobre ventanas del calendario de actividad + feriados/excepciones.
- Hallazgos críticos:
  - A1060: reparto correcto 54/108/54 por media jornada (no 72/72/72).
  - A1160: desalineación visual por bucket etiquetado en Usage (54/108/108/54), afectando semanas W38/W39.
- Curva semanal consolidada y validada contra extracto semanal P6 (Proyecto SAG 3):
  W30=36, W31=180, W32=180, W33=396, W34=1080, W35=1566, W36=1404, W37=1350, W38=378, W39=216 (BAC=6786, 100%).
- Decisión de producto: formalizar estándar transversal (no OT-específico) con modo `logic` y modo `p6_visual` para reproducibilidad entre programas.

## 2026-03-10 16:08 (UTC-3)
- Se ordena la base documental del proyecto para pruebas conjuntas XER + DB.
- Se detectan fixtures externos en `001_Prueba Externa/`: `15682-SEG al 14-12.xer` y `15682-SEG-LB.xer`.
- Se crea `docs/XER_DB_VALIDATION_FLOW.md` como flujo operativo único de validación cruzada.
- Se normaliza `INDEX.csv` para reflejar artefactos vigentes y carpeta de fixtures.
- Próximo objetivo técnico: comparador reusable `XER vs DB` parametrizable y sin rutas hardcodeadas.

## 2026-03-11 15:18 (UTC-3)
- Se ejecuta campaña intensiva de pruebas de carga directa en SQLite P6 usando OT-1844 (`W012` + baseline asociada) como banco de prueba operacional.
- Flujo probado: foco de programa → validación de LB → fijación de data date → generación de Excel de revisión → carga parcial de avances → correcciones iterativas sobre HH, fechas, costos y reflejo en UI P6.
- Hallazgos validados:
  - Actualizar solo `TASKRSRC` no basta; P6 lee también resumen laboral de `TASK` (`ACT_WORK_QTY`, `REMAIN_WORK_QTY`, `TARGET_WORK_QTY`).
  - Cierres al 100% requieren sincronizar también costos (`ACT_REG_COST`, `REMAIN_COST`) para evitar at-complete inflado.
  - Fechas sin hora provenientes de Excel no deben cargarse como `00:00`; deben convertirse a jornada real según calendario/lógica de actividad para evitar duración actual 0.
  - La carga debe respetar `COMPLETE_PCT_TYPE` del proyecto/actividad (`CP_Drtn` en este caso) y no asumir Units % Complete como regla universal.
  - Las pruebas parciales deben excluir filas ambiguas (sin inicio o sin término) y tratar por separado cierres 100% vs avances parciales.
- Resultado: se consolida un patrón operativo reutilizable para el agente en `P6-Standalone-Automation`, pendiente de formalización en script reusable de carga segura desde Excel hacia DB.

## 2026-03-11 16:00 (UTC-3)
- Se ejecuta auditoría de scripts del proyecto y se clasifica el estado real de la carpeta `scripts/`.
- Nuevo documento: `docs/SCRIPT_AUDIT_2026-03-11.md` con separación entre scripts productivos, prototipos y temporales.
- Nuevo resumen operativo vivo: `docs/OPERATING_SUMMARY_2026-03-11.md`.
- Se agrega comparador reusable inicial: `scripts/compare_xer_db_weekly.py` para contraste semanal XER vs DB a partir de CSV normalizados.
- Validación ejecutada con fixture 15682/LB vs DB (`compare_xer_db_26379_reusable.csv`): 35 semanas, `MAX_ABS_DELTA_VALUE=173.5199`, `MAX_ABS_DELTA_CUM=635.4370`.
- Se reindexa RAG del proyecto incorporando el resumen operativo; colección `p6_standalone_automation` pasa de 400 a 767 chunks.
- Resultado: la consulta semántica de “estado actual operativo del proyecto” pasa a recuperar `OPERATING_SUMMARY_2026-03-11` como top hit.

## 2026-03-11 16:21 (UTC-3)
- Se consolida primer cargador seguro reusable `scripts/load_progress_excel_to_p6db.py` para avances Excel -> DB SQLite P6.
- Reglas incorporadas al flujo: dry-run por defecto, respaldo previo en `--apply`, rechazo de filas ambiguas, normalización de fechas mismo día sin hora, sincronización `TASKRSRC` -> `TASK`, alineación de `COMPLETE_PCT_TYPE` y sincronización de costos laborales.
- Se amplía `scripts/pilot_audit.py` con tres checks post-carga críticos: desfase `TASK` vs `TASKRSRC`, completas con `ACT_WORK_QTY=0`, completas con `REMAIN_COST labor > 0`.
- Dry-run validado con Excel OT-1844 W012 v3 sobre `PROJ_ID=26432`: `CANDIDATES=33`, `PREVIEW_ROWS=19`, `ERROR_ROWS=14`, `APPLIED_ROWS=0`.
- Reportes generados: `data/load_progress_preview_26432_20260311_162145.csv`, `data/load_progress_errors_26432_20260311_162145.csv`, `data/load_progress_summary_26432_20260311_162145.md`.
- Auditoría extendida sobre estado actual de `PROJ_ID=26432`: `NO_PREDECESSOR=0`, `OVERDUE_MILESTONE=0`, `TASK_WORK_MISMATCH_LABOR=0`, `COMPLETE_ZERO_ACT_WORK=0`, `COMPLETE_WITH_REMAIN_COST=0`.

## 2026-03-11 16:41 (UTC-3)
- Se reordena internamente la carpeta `scripts/` por capas operativas para bajar ruido y separar código productivo de experimental.
- Nueva estructura: `scripts/core`, `scripts/support`, `scripts/mutations`, `scripts/prototypes`, `scripts/archive_tmp`.
- Se archivan 38 scripts `tmp_*` en `scripts/archive_tmp/`.
- Se mueven los scripts productivos principales a `scripts/core/`: `load_progress_excel_to_p6db.py`, `pilot_audit.py`, `compare_xer_db_weekly.py`, `xer_update.py`.
- Se verifican rutas nuevas ejecutando `--help` en `scripts/core/load_progress_excel_to_p6db.py` y `scripts/core/pilot_audit.py` con resultado OK.

## 2026-03-11 16:56 (UTC-3)
- Se incorpora `scripts/p6_utils.py` como capa compartida en `master` para conexión DB, NEXTKEY, timestamps, split3, clonación de recursos e inserción genérica.
- Se agrega `tests/test_p6_utils.py` con validación ejecutable vía `unittest` (3 tests OK).
- Se migran scripts de `mutations/` con duplicación real de helpers (`apply_wbs_crew_split.py`, `replace_resource_with_three_ops.py`, `apply_distinct_hh_resources.py`, `create_project_under_simtexx.py`) para importar desde `p6_utils`.
- Se migran scripts de `support/` con DB hardcodeada a `argparse --db` + `open_db` (`check_resource_types.py`, `check_taskrsrc_types.py`, `check_root_154616.py`, `list_eps_level1.py`, `show_nextkeys.py`, `verify_hh_update.py`, `verify_multi_wbs_crew.py`, `verify_projects_under_root.py`, `inspect_sqlite.py`).
- Verificaciones ejecutadas: `python -m compileall projects/P6-Standalone-Automation/scripts tests/test_p6_utils.py` OK; `python -m unittest tests.test_p6_utils -v` OK.

## 2026-03-11 17:19 (UTC-3)
- Se crea `scripts/core/pv_engine.py` como motor dual único con interfaz estable: `--base-xer`, `--upd-xer`, `--db`, `--proj-id`, `--cutoff`, `--mode`, `--out-dir`, `--format`.
- Se rescatan del prototipo `weekly_control_report_v2.py` exactamente las piezas base: `parse_table`, `safe_float`, `safe_dt`, `spread_lv`, `week_label` y bucket semanal por lunes; no se rescatan estructura ni constantes hardcodeadas.
- Se separa internamente en cuatro capas: `load()`, `compute()`, `compare()`, `export()`.
- Se fija salida estable con columnas: `week`, `pv_week`, `pv_cum`, `ev_cum`, `sv`, `spi`.
- `mode=p6_visual` queda documentado como stub intencional; `mode=logic` queda ejecutable.
- Tests mínimos agregados en `tests/test_pv_engine.py` con `unittest` para `spread_lv` y `week_label` (OK).
- Verificaciones ejecutadas: `python -m unittest tests.test_pv_engine -v` OK; `pv_engine.py --mode p6_visual` OK; `pv_engine.py --mode logic` OK.
