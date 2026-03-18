# XER + DB Validation Flow

## Objetivo
Tener un flujo único y repetible para validar un proyecto en dos fuentes a la vez:
- **XER** como snapshot/export de intercambio
- **SQLite de P6 Standalone** como base operativa

La meta no es asumir que ambas fuentes siempre calzan al 100%, sino detectar y explicar diferencias con trazabilidad.

## Casos de prueba disponibles hoy
Carpeta: `projects/P6-Standalone-Automation/001_Prueba Externa`

Archivos detectados:
- `15682-SEG al 14-12.xer`
- `15682-SEG-LB.xer`

Estos quedan definidos como **fixtures externos iniciales** para pruebas comparativas.

## Flujo recomendado

### 1) Registrar el caso
Para cada prueba dejar claro:
- nombre del proyecto
- archivo baseline XER
- archivo update/control XER (si existe)
- si existe correspondencia con una DB SQLite
- `proj_id` esperado en DB, si ya se conoce
- qué se quiere validar primero: PV / EV / forecast / recursos / importación

### 2) Extraer snapshot mínimo de ambas fuentes
**Desde XER**
- `PROJECT`
- `TASK`
- `TASKRSRC`
- `RSRC`
- `CALENDAR` cuando el cálculo semanal dependa de calendario real

**Desde DB SQLite**
- `PROJECT`
- `TASK`
- `TASKRSRC`
- `RSRC`
- `CALENDAR`
- tablas time-phased/financieras si el caso lo requiere

### 3) Correr validaciones base obligatorias
1. `Σ TASKRSRC.target_qty = BAC`
2. `Σ semanal = BAC`
3. `Σ por actividad = TARGET_QTY esperado`
4. filtro estricto `RSRC_TYPE='RT_Labor'` cuando se hablen HH de mano de obra
5. consistencia de fechas de inicio/fin y calendario usado
6. trazabilidad de diferencias por actividad y por bucket semanal

### 4) Elegir modo de cálculo
- **logic**: distribución por horas efectivas de solape usando calendario real + excepciones
- **p6_visual**: reproducir, cuando aplique, la lógica visible del Usage Spreadsheet aunque exista corrimiento de etiqueta/bucket

Regla: no mezclar ambos modos en el mismo informe sin declararlo explícitamente.

### 5) Emitir resultado
Cada corrida debería dejar:
- resumen ejecutivo del caso
- supuestos usados
- BAC / EV / ETC / EAC / PV si aplica
- diferencias XER vs DB
- listado de actividades conflictivas
- decisión: OK / revisar / no comparable todavía

## Checks prioritarios para el próximo XER externo
Cuando llegue un XER nuevo, el orden sugerido es:
1. **Integridad del archivo**: cabecera `ERMHDR`, cierre `%E`, tablas presentes
2. **Inventario del proyecto**: PROJECT / TASK / TASKRSRC / RSRC
3. **BAC laboral**: `TASKRSRC.target_qty` con `RT_Labor`
4. **Curva semanal baseline**
5. **Contraste contra DB** si existe equivalencia del proyecto
6. **Diferencias de calendario** antes de concluir desvíos

## Scripts actuales que ya sirven como base
- `scripts/inspect_sqlite.py`
- `scripts/pilot_audit.py`
- `scripts/weekly_control_report.py`
- `scripts/weekly_control_report_v2.py`
- `scripts/weekly_hh_cutoff_curve.py`
- `scripts/xer_update.py`
- `scripts/tmp_verify_xer_both.py` *(útil como referencia, pero aún temporal)*

## Pendiente inmediato
Formalizar un script reusable de comparación **XER vs DB** con entrada por parámetros, sin rutas hardcodeadas, y salida en Markdown/CSV para revisión rápida.
