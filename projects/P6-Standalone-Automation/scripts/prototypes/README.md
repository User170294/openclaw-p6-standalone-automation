# scripts/prototypes — Referencia histórica

Estos scripts son prototipos que precedieron al engine productivo actual.
**No usar en producción.** Contienen rutas absolutas, fechas y nombres de proyecto hardcodeados específicos de OT-1844.

## Para qué sirven
- Documentan la evolución del razonamiento antes de generalizar el código
- Son el origen conceptual de `scripts/core/pv_engine.py` y `scripts/core/generate_recovery_excel.py`
- Útiles para entender decisiones de diseño del engine actual

## Scripts y su equivalente productivo

| Prototipo | Reemplazado por |
|-----------|----------------|
| `weekly_control_report.py` | `scripts/core/pv_engine.py` |
| `weekly_control_report_v2.py` | `scripts/core/pv_engine.py` |
| `weekly_hh_cutoff_curve.py` | `scripts/core/pv_engine.py` |
| `compare_weekly_curve_weekdays.py` | `scripts/core/compare_xer_db_weekly.py` |
| `summary_1844.py` | `scripts/core/report_generator.py` |
| `run_weekly_report.ps1` | Flujo CLI con `pv_engine.py` + `report_generator.py` |
