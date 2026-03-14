# FOCUS.md — P6-Standalone-Automation
<!-- Actualizar al cierre de cada sesión. Lilit lee esto PRIMERO al hacer foco. -->
<!-- Última actualización: 2026-03-14 -->

## Estado actual
Fase de **consolidación operativa**. El engine EVM está funcional y validado para OT-1844.
El flujo end-to-end (captura Excel → carga DB → engine → reporte HTML) está implementado
pero aún no validado completamente en producción.

**Tests:** 15/15 en verde (9 raíz + 6 proyecto)
**Último commit:** `e55a0fc` — refactor(SKILL.md): separar reglas genéricas de datos OT-1844

## Proyecto de referencia — OT-1844
- **Nombre:** Fabricación Bandejas Agua Lavado Celdas (Rev. B)
- **BAC:** 8,100 HH
- **proj_id baseline:** 26258 → fuente de PV
- **proj_id actualizado W012:** 26432 → fuente de EV + Remaining
- **DB SQLite:** `C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db`
- **Valor de referencia:** EV acum W11 = 4,114.80 HH (50.80%)

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
1. Validar engine end-to-end contra P6 real en producción (OT-1844 W012)
2. Comparador reusable XER vs DB sin rutas hardcodeadas
3. Modo dual `logic` vs `p6_visual` con validación automática
4. Endurecer cargador Excel → DB con validación horaria contra calendario real
5. Flujo completo: captura → carga → engine → reporte (integración end-to-end)

## Contexto de arquitectura
El proyecto está en camino a soporte multi-proyecto. Actualmente hardcodeado para OT-1844.
Refactorización multi-proyecto planificada después de estabilizar el flujo end-to-end.

## Instrucción para Lilit al hacer foco
1. Leer este archivo
2. Leer `SKILL.md` en la raíz del repo
3. Correr tests: `python -m pytest tests/ -q` y `python -m pytest projects/P6-Standalone-Automation/tests/ -q`
4. Verificar que estás en 15/15 antes de tocar cualquier cosa
5. Solo si necesitas ampliar contexto: revisar `MEMORY.md` y `git log --oneline -10`
