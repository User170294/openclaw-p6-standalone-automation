# MEMORY - P6-Standalone-Automation

## Decisiones
- Proyecto creado para centralizar automatización de Primavera P6 Standalone.
- Se prioriza seguridad operativa: dry-run, permisos mínimos, auditoría y backups.
- Base SQLite activa confirmada (2026-02-27): `C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db`.

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

## Pendientes
- Formalizar en script reusable un modo dual: `logic` vs `p6_visual` con validación automática contra export de Usage.
- Diseñar job piloto y criterios de éxito.
