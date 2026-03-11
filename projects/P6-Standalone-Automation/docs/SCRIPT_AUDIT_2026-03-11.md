# Script Audit — P6-Standalone-Automation — 2026-03-11

## Resumen ejecutivo

El proyecto ya tiene una base útil, pero está mezclada con bastante código temporal (`tmp_*`) y scripts muy específicos para OT-1844.

La conclusión práctica es esta:

- **Sí hay piezas reutilizables de verdad**.
- **No conviene tratar toda la carpeta `scripts/` como productiva**.
- El siguiente salto correcto es separar el proyecto en tres capas:
  1. **inspección/auditoría**,
  2. **cálculo/reportabilidad**,
  3. **mutaciones controladas (XER/DB)**.

---

## Clasificación de scripts

## 1) Scripts productivos o casi productivos

### `scripts/pilot_audit.py`
**Estado:** usable ahora

**Sirve para:**
- auditoría base sobre SQLite P6,
- detectar actividades sin predecesora,
- detectar hitos/actividades vencidas,
- dejar salida CSV + MD.

**Fortalezas:**
- parametrizable por DB y `PROJ_ID`,
- salida clara,
- sin escritura en DB,
- bueno como chequeo inicial.

**Brechas:**
- set de reglas aún chico,
- no separa severidad,
- no consolida múltiples chequeos en formato estable para automatización posterior.

**Veredicto:** conservar y extender.

---

### `scripts/xer_update.py`
**Estado:** base muy valiosa, pero aún parcial

**Sirve para:**
- parche seguro de XER por líneas,
- conservar envolvente nativa (`ERMHDR`, `%E`),
- merge de recursos,
- actualización parcial de progreso por filtro.

**Fortalezas:**
- corrige el error crítico de reserializar XER completo,
- incluye chequeos de seguridad,
- valida conservación de HH objetivo labor.

**Brechas:**
- mezcla dos responsabilidades en un solo script,
- progreso por `task_name contains` es demasiado frágil para operación seria,
- no modela plan de cambios/preview detallado por actividad,
- no genera reporte estructurado de diferencias antes/después.

**Veredicto:** conservar como núcleo de mutación XER; luego dividir en módulos o subcomandos.

---

### `scripts/replace_resource_with_three_ops.py`
**Estado:** útil pero altamente específico

**Sirve para:**
- reemplazo 1→3 de recurso en SQLite,
- creación de recursos OP1/OP2/OP3,
- reparto de HH y costos,
- actualización transaccional con rollback.

**Fortalezas:**
- usa transacción,
- maneja `NEXTKEY`,
- deja salida verificable,
- encapsula una operación real ya validada.

**Brechas:**
- lógica amarrada al caso 1→3,
- hardcode implícito del modelo de costos,
- no separa plan/apply/report,
- no recalcula por sí sola la distribución temporal (`TARGET_QTY_PER_HR`, `REMAIN_QTY_PER_HR`).

**Veredicto:** conservar como caso de referencia, no como API final.

---

### `scripts/fix_op_rate_spread.py`
**Estado:** correctivo reusable de nicho

**Sirve para:**
- corregir distribución temporal después del split de recursos,
- ajustar `TARGET_QTY_PER_HR` y `REMAIN_QTY_PER_HR`.

**Fortalezas:**
- simple,
- focalizado,
- resuelve un hallazgo validado.

**Brechas:**
- depende del flujo anterior,
- asume división en 3,
- no verifica por actividad antes/después.

**Veredicto:** mantener como utilitario técnico; idealmente absorberlo dentro de un flujo unificado de reemplazo de recursos.

---

## 2) Scripts útiles como prototipo, pero no como producto todavía

### `scripts/weekly_control_report.py`
**Estado:** prototipo funcional orientado a OT-1844

### `scripts/weekly_control_report_v2.py`
**Estado:** depuración/experimento

### `scripts/weekly_hh_cutoff_curve.py`
**Estado:** método útil pero simplificado

### `scripts/compare_weekly_curve_weekdays.py`
**Estado:** comparador puntual, no universal

**Observación conjunta:**
Estos scripts capturan aprendizaje real del proyecto, pero hoy están demasiado amarrados a:
- rutas específicas,
- semanas específicas,
- OT-1844,
- supuestos simplificados de calendario o corte.

**Veredicto:**
- sirven como evidencia del método,
- no deberían presentarse como capa final reusable sin refactor.

---

## 3) Scripts de soporte/inspección que conviene conservar

- `scripts/inspect_sqlite.py`
- `scripts/list_projects.py`
- `scripts/list_wbs_level.py`
- `scripts/project_snapshot.py`
- `scripts/show_nextkeys.py`
- `scripts/verify_*`
- `scripts/check_*`

**Veredicto:** útiles para diagnóstico y exploración; mantener, pero etiquetarlos explícitamente como herramientas de soporte.

---

## 4) Scripts temporales / deuda técnica visible

Hay una cantidad alta de archivos `tmp_*` dentro de `projects/P6-Standalone-Automation/scripts/`.

Eso hoy mete ruido en tres frentes:

1. dificulta saber qué es productivo,
2. complica RAG y recuperación semántica,
3. hace más riesgoso reutilizar algo equivocado.

**Veredicto:**
- moverlos a `tmp/` o `scripts/archive/`,
- o bien dejar solo los realmente vigentes y documentados.

---

## Recomendación de estructura objetivo

## Capa A — lectura / diagnóstico
- `inspect_sqlite.py`
- `pilot_audit.py`
- `project_snapshot.py`
- `compare_xer_db_weekly.py`

## Capa B — cálculo / control semanal
- motor semanal por calendario real,
- exportadores CSV/MD,
- modo `logic` vs `p6_visual`.

## Capa C — mutación segura
- `xer_update.py` (refactorizado)
- cargador seguro Excel → DB
- reemplazo de recursos con validación integrada

---

## Prioridad recomendada

1. **Formalizar comparador reusable XER vs DB**.
2. **Crear resumen operativo vivo del proyecto e indexarlo**.
3. **Separar scripts productivos de temporales**.
4. **Convertir aprendizajes de DB load en script reusable**.

---

## Conclusión

El proyecto **sí está maduro para consolidación**, no para limpieza cosmética solamente.

Lo más valioso que ya existe es:
- conocimiento operativo validado,
- mutación segura de XER por parche,
- auditoría SQLite,
- aprendizaje real sobre PV/EV y carga DB.

Lo más urgente no es escribir desde cero, sino:
- **ordenar**,
- **parametrizar**,
- **dejar un camino productivo único**.
