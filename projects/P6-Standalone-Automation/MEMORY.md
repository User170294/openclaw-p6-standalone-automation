# MEMORY - P6-Standalone-Automation

## Decisiones
- Proyecto creado para centralizar automatización de Primavera P6 Standalone.
- Se prioriza seguridad operativa: dry-run, permisos mínimos, auditoría y backups.
- Base SQLite activa confirmada (2026-02-27): `C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db`.
- El motor `pv_engine` opera sobre DB SQLite como fuente primaria. XER se soporta como fuente secundaria para interoperabilidad únicamente.

## Valores específicos OT-1844 movidos desde SKILL.md (2026-03-13)
- `proj_id` baseline: `26258`
- `proj_id` actualizado: `26432`
- BAC de referencia: `8100 HH`
- Valor de referencia EV acumulado W11: `4114.80 HH`

## Aprendizajes operativos (2026-03-12) — Early Remaining Labor Units
- **CRÍTICO**: Para distribuir Early Remaining Labor Units por semana, usar `RESTART_DATE` → `REEND_DATE`, **NO** cutoff → fin.
- El campo `REMAIN_EARLY_END_DATE` no existe en TASKRSRC de esta DB; los campos correctos son:
  - `RESTART_DATE` = fecha inicio del trabajo remanente
  - `REEND_DATE` = fecha fin del trabajo remanente (fallback a `TARGET_END_DATE` si es null)
- Error corregido en `pv_engine.py`: antes se distribuía desde cutoff hacia fin, lo que generaba forecast incorrecto.
- Validación obligatoria: `EV + REM = BAC` (ej. 747 + 7353 = 8100 para OT 1844_B-PRUEBA).
- Caso de prueba validado: `26483 | OT 1844_B-PRUEBA` con baseline `26484`.

## Aprendizajes operativos (2026-02-27)
- En reemplazo de recurso 1→N (ej. `9398` → `OP1/OP2/OP3`) no basta con conservar `TARGET_QTY`/HH totales.
- Para mantener curva semanal y % de avance equivalentes al original, también se debe ajustar proporcionalmente `TARGET_QTY_PER_HR` y `REMAIN_QTY_PER_HR` en `TASKRSRC`.
- Validación obligatoria post-cambio entre proyecto modificado vs baseline: comparar `SUM(TARGET_QTY)`, `SUM(TARGET_QTY_PER_HR)`, `SUM(REMAIN_QTY_PER_HR)` y consistencia por actividad.
- Diferencias residuales de ~0.0000x pueden aparecer por redondeo flotante; son aceptables si el agregado coincide.
- Criterio oficial de seguimiento semanal OT-1844 (definido por usuario): usar curva S de Labor Units en modo time-phased laboral (L-V), equivalente a la lectura de Activity Usage Profile (Baseline/Planned Value Labor Units), evitando corte simple por fecha fin.

## Estándar validado (2026-03-09) — PV/EV semanal desde XER (OT-1844)
- Fuente oficial para PV baseline: `TASKRSRC.target_qty` filtrando `rsrc_type=RT_Labor` y `proj_id` del bloque `PROJECT`.
- Distribución semanal: prorrateo diario uniforme entre `target_start_date` y `target_end_date` en días laborales **L-V** (incluyendo ambos extremos), con agregación por semana ISO (**lunes-domingo**).
- BAC validado: `SUM(target_qty)=8100 HH`.
- Hitos de validación baseline (Rev.B): W08=1134 HH (14.00%), W09=2295 HH (28.33%), W10=3771 HH (46.56%).
- EV real al corte W11 (`last_recalc_date=2026-03-08 23:59`): 3394.8 HH (41.91%).
- Nota de alcance: este estándar replica el control operativo requerido; no aplica curvas `target_crv` ni excepciones de calendario avanzadas de P6 salvo instrucción explícita.

## Estándar transversal validado (2026-03-09 noche) — aplicable a cualquier programa
- No usar regla única L-V ni prorrateo diario plano como verdad universal.
- Motor base para PV semanal debe usar, en este orden:
  1) `TASKRSRC` (`RSRC_TYPE='RT_Labor'`) como fuente HH,
  2) calendario de actividad (`TASK.CLNDR_ID`) y no asumir calendario fijo,
  3) excepciones/feriados desde `CALENDAR.CLNDR_DATA` (`Exceptions`),
  4) distribución por **horas efectivas de solape** (inicio/fin con hora + ventanas del calendario),
  5) agregación por semana ISO.
- Para comparaciones contra vista P6 (Usage Spreadsheet), considerar explícitamente posible diferencia entre:
  - fecha lógica de trabajo,
  - fecha etiquetada del bucket visual.
- Validaciones obligatorias antes de emitir informe:
  - ΣHH semanal = BAC,
  - ΣHH por actividad = `TARGET_QTY`,
  - trazabilidad de actividades con desvío por bucket/etiqueta.

## Caso de prueba crítico (OT-1616_0 - B1)
- Actividad A1060 demostró que prorrateo por día plano falla en tareas con media jornada; el reparto correcto se obtiene por peso horario:
  - 13-sep: 54 HH, 15-sep: 108 HH, 16-sep: 54 HH (total 216).
- Actividad A1160 evidenció desplazamiento visual de bucket en Usage Spreadsheet (aparición de 54 HH en 23-sep pese a finish 22-sep 12:30).
- Curva semanal validada contra extracto semanal P6 para Proyecto SAG 3:
  - W30 36, W31 180, W32 180, W33 396, W34 1080, W35 1566, W36 1404, W37 1350, W38 378, W39 216 (BAC 6786 = 100%).

## Aprendizajes operativos (2026-03-11) — pruebas de carga DB directa sobre programa OT-1844
- Para cargar avances en SQLite P6 no basta con actualizar `TASKRSRC`; también deben sincronizarse los campos resumen de `TASK` usados por la UI de P6 (`ACT_WORK_QTY`, `REMAIN_WORK_QTY`, `TARGET_WORK_QTY`). Si no, P6 puede mostrar actividades al 100% con Actual Labor Units = 0 aunque `TASKRSRC.ACT_REG_QTY` esté correcto.
- En cierres al 100% también deben sincronizarse costos en `TASKRSRC`: `ACT_REG_COST = TARGET_COST` y `REMAIN_COST = 0`. Si no, el campo At Complete Labor Cost queda inflado (ej. budget 9, at complete 18 por `REMAIN_COST` residual).
- Si el Excel trae fecha sin hora y usuario indica mismo día de inicio/fin, debe interpretarse como jornada completa compatible con el calendario/plan de la actividad, no `00:00` a `00:00`. Dejar `00:00` genera duración actual 0 en P6.
- Antes de grabar fechas reales, verificar compatibilidad con `TASK.CLNDR_ID`. Si la fecha real cae fuera del calendario, ajustar el calendario de la actividad o usar una lógica horaria compatible antes de cerrar la actividad.
- El `% Complete Type` de la actividad debe alinearse con el del proyecto/base cuando no exista razón explícita para diferir. En el caso validado, proyecto y actividades operan con `CP_Drtn`; por lo tanto, no aplicar ciegamente la lógica de `% unidades` como sustituto del porcentaje del proyecto.
- Para pruebas parciales desde Excel, no cargar filas ambiguas. Si falta fecha de inicio o término, separar esos casos y no forzar cierres. Regla segura para prueba: cargar solo filas con `%`, inicio real y término real explícitos cuando el objetivo es cerrar al 100%.
- Secuencia operativa mínima para carga robusta: respaldo DB → fijar data date → validar `% complete type` → validar calendario → aplicar HH/fechas/estado en `TASKRSRC` + `TASK` → sincronizar costos → verificar en P6/UI.

## Pendientes
- Formalizar en script reusable un modo dual: `logic` vs `p6_visual` con validación automática contra export de Usage.
- Construir comparador reusable `XER vs DB` por parámetros, evitando rutas hardcodeadas y salidas ad-hoc.
- Diseñar job piloto y criterios de éxito.
- Endurecer el cargador seguro `scripts/load_progress_excel_to_p6db.py` con validación horaria por calendario P6 real (`CALENDAR.CLNDR_DATA`) y manejo más rico de parciales/ambigüedades.

## Implementación consolidada (2026-03-11 tarde)
- Se formaliza `scripts/load_progress_excel_to_p6db.py` como primer cargador seguro reusable de avances Excel -> DB SQLite P6.
- El script trabaja en `dry-run` por defecto, genera preview/errores, exige respaldo antes de `--apply`, sincroniza `TASKRSRC` y resumen `TASK`, alinea `COMPLETE_PCT_TYPE` con el proyecto y corrige fechas mismo día sin hora heredando horas planificadas o usando jornada por defecto.
- Se amplía `scripts/pilot_audit.py` con checks post-carga para detectar: desfase `TASK` vs suma labor `TASKRSRC`, actividades completas con `ACT_WORK_QTY=0` y actividades completas con `REMAIN_COST>0`.
- Validación dry-run inicial sobre OT-1844 W012 (`PROJ_ID=26432`): 33 filas candidatas, 19 listas para preview y 14 rechazadas por ambigüedad/missing fechas; la auditoría post-carga del estado actual del programa devuelve 0 hallazgos en los checks nuevos.

## Estado de preparación para pruebas externas (2026-03-10)
- Se define `001_Prueba Externa/` como carpeta de fixtures XER para validación cruzada.
- Flujo operativo documentado en `docs/XER_DB_VALIDATION_FLOW.md`.
- `INDEX.csv` normalizado para reflejar artefactos vigentes del proyecto.

## Aprendizaje operativo (2026-03-13) � Remaining Early W12 debe respetar Early Start + calendario real
- Se detect� desv�o al calcular recovery W12 usando una aproximaci�n simplificada del remaining.
- Caso testigo validado: `A3880` (`REMAIN_QTY=162`, `REMAIN_QTY_PER_HR=6`, calendario `7475`, `EARLY_START_DATE=2026-03-19 08:00`, `EARLY_END_DATE=2026-03-23 18:00`).
- Resultado correcto por semana: **W12 = 108 HH**, **W13 = 54 HH**.
- Regla corregida: para `Remaining Early` no basta con repartir `REMAIN_QTY` entre corte y `EARLY_END_DATE`; se debe usar `max(corte+1s, EARLY_START_DATE)` como inicio efectivo, junto con `TASK.CLNDR_ID`, `CALENDAR.CLNDR_DATA`, horas efectivas de solape y consistencia con `REMAIN_QTY_PER_HR`.
- Mejora aplicada en `scripts/core/pv_engine.py` (modo DB): el remaining ahora usa `EARLY_START_DATE` + `EARLY_END_DATE` + calendario real para distribuir `re_week`.
- Resultado recalculado W12: `Remaining Early = 1872.0 HH`. Archivo de respaldo anal�tico: `projects/P6-Standalone-Automation/data/recovery_W12_recalc_2026-03-13.md`.
