# FOCUS.md — P6-Standalone-Automation
<!-- Actualizar al cierre de cada sesión. Lilit lee esto PRIMERO al hacer foco. -->
<!-- Última actualización: 2026-03-14 -->

## Estado actual
Fase de **consolidación operativa** con base documental y operativa ya ordenada.
El engine EVM está funcional y validado para OT-1844, el cargador reusable Excel → DB existe,
el comparador reusable XER vs DB ya fue incorporado, y el flujo end-to-end
(captura Excel → carga DB → engine → reporte HTML) está implementado.

Lo que sigue pendiente no es construir el flujo base, sino **cerrar la validación end-to-end real en producción**
y endurecer los bordes operativos (horarios/calendario real, contraste automático, modo visual P6).

**Tests:** 15/15 en verde verificados hoy (9 raíz + 6 proyecto)
**Último commit del proyecto:** `c4cddef` — `chore: fix gitignore - add pycache, destrackear privados`
**Commit funcional relevante previo:** `6895ed1` — `docs: add FOCUS.md - contexto canónico de arranque rápido para Lilit`

## Proyecto de referencia — OT-1844
- **Nombre:** Fabricación Bandejas Agua Lavado Celdas (Rev. B)
- **BAC:** 8,100 HH
- **proj_id baseline:** 26258 → fuente de PV
- **proj_id actualizado W011:** 26485 (OT 1844_B-W012) → fuente de EV + Remaining (26432 ya no existe en DB)
- **DB SQLite:** `C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db`
- **Valor de referencia:** EV acum W11 = 4,669.20 HH (57.64%) — corte 15-mar-2026

## Regla crítica — NO MEZCLAR PROGRAMAS
PV siempre de `proj_id=26258`. EV y Remaining siempre de `proj_id=26432`. Sin excepciones.

## Scripts core activos
| Script | Función |
|--------|---------|
| `pv_engine.py` | Motor EVM: PV / EV / Remaining / Forecast |
| `report_generator.py` | Reporte HTML dark con Chart.js (estándar validado) |
| `load_progress_excel_to_p6db.py` | Carga avances Excel → DB SQLite |
| `generate_progress_capture_excel.py` | Genera Excel de captura semanal |
| `generate_recovery_excel.py` | Reporte de recuperación semanal |
| `prepare_load_workbook_from_capture.py` | Prepara workbook para carga |
| `pilot_audit.py` | Auditoría post-carga |
| `compare_xer_db_weekly.py` | Comparador XER vs DB |

## Decisiones técnicas vigentes
- **Fuente primaria:** DB SQLite. XER solo para interoperabilidad/validación
- **Engine DB lee de tabla `TASK`** (no TASKRSRC) con campos:
  `TARGET_WORK_QTY`, `ACT_WORK_QTY`, `REMAIN_WORK_QTY`, `EARLY_START_DATE`, `EARLY_END_DATE`
- **Remaining Early:** usar `max(corte+1s, EARLY_START_DATE)` → `EARLY_END_DATE` + calendario real
- **week_label():** siempre genera `W##` (nunca `ISO####-W##`)
- **Template HTML:** dark + Chart.js con curvas PV / EV / Forecast + barras Remaining
- **XER:** nunca reserializar completo; solo parche incremental

## Brechas pendientes (prioridad)
1. Validar flujo end-to-end real contra P6 en producción (OT-1844 W012)
2. Endurecer cargador Excel → DB con validación horaria y calendario real
3. Cerrar modo dual `logic` vs `p6_visual` con contraste/validación automática
4. Terminar de desacoplar rutas hardcodeadas y parámetros operativos para reutilización multi-caso
5. Formalizar la integración completa de captura → carga → engine → reporte como flujo estable de operación

## Contexto de arquitectura
La arquitectura sigue siendo **DB-first** y el proyecto ya tiene piezas reusables visibles
(`pv_engine.py`, `load_progress_excel_to_p6db.py`, `compare_xer_db_weekly.py`, `pilot_audit.py`).

Aun así, el caso operacional dominante sigue siendo OT-1844 y todavía existen supuestos/rutas
que deben desacoplarse antes de declarar soporte multi-proyecto real.
La refactorización multi-proyecto queda después de estabilizar y validar el flujo end-to-end productivo.

## Instrucción para Lilit al hacer foco
1. Leer este archivo
2. Leer `SKILL.md` en la raíz del repo
3. Correr tests: `python -m pytest tests/ -q` y `python -m pytest projects/P6-Standalone-Automation/tests/ -q`
4. Verificar que estás en 15/15 antes de tocar cualquier cosa
5. Revisar `git log --oneline -5 -- projects/P6-Standalone-Automation` para detectar delta reciente
6. Solo si necesitas ampliar contexto: revisar `MEMORY.md` y `LOG.md`
