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

## Pendientes
- Definir stack de automatización (Python + PowerShell).
- Diseñar job piloto y criterios de éxito.
