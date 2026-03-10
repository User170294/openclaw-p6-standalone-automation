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
