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

## Pendientes
- Definir stack de automatización (Python + PowerShell).
- Diseñar job piloto y criterios de éxito.
