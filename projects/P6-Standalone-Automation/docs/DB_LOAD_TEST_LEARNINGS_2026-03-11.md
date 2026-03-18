# DB Load Test Learnings — OT-1844 — 2026-03-11

## Contexto
Pruebas de carga directa sobre la DB SQLite de P6 Standalone usando OT-1844 como banco de prueba operativo.

- DB base: `C:\Users\josej\OneDrive\Documentos\PPMDBSQLite_20221109_BBDD_JJC_Rev B.db`
- Programa update probado: `26432 | OT 1844_B-W012`
- Baseline asociada: `26433 | OT 1844_B-W011-1 - B1`
- Data date usado para la prueba: `2026-03-15 23:59:00`

## Objetivo de la sesión
Validar una forma segura y repetible de cargar avances desde Excel hacia P6 SQLite sin romper:
- HH reales/remanentes
- costos
- porcentaje de avance
- fechas reales
- calendarios
- lectura visible en la UI de P6

---

## Pruebas realizadas

### 1) Revisión base del programa limpio
Se verificó:
- baseline enlazada
- `% Complete Type` del proyecto
- `Duration Type`
- calendarios usados por actividades
- BAC / EV / ETC del programa

### 2) Fijación de data date
Se actualizó el programa de prueba a:
- `LAST_RECALC_DATE = 2026-03-15 23:59:00`
- `APPLY_ACTUALS_DATE = 2026-03-15 23:59:00`

### 3) Generación de Excel de revisión
Se generaron varias versiones de Excel para capturar:
- actividades que deberían tener avance al corte
- `% avance a cargar`
- fecha inicio real
- fecha término si queda al 100%

### 4) Carga parcial de prueba
Se aplicó carga solo sobre Entrega 1 y 2, inicialmente con filas cerrables al 100%.

### 5) Correcciones iterativas
Durante la prueba se detectaron y corrigieron inconsistencias en:
- fechas reales
- HH resumen visibles en P6
- costos remanentes

---

## Errores detectados y solución aplicada

## Error 1 — Cargar solo `TASKRSRC` no refleja bien las HH en P6
### Síntoma
En P6 algunas actividades aparecían:
- `TK_Complete`
- con fechas reales cargadas
- pero con **Actual Labor Units = 0** en la UI

### Ejemplo
- `A3230`

### Causa raíz
La carga actualizó correctamente:
- `TASKRSRC.ACT_REG_QTY`
- `TASKRSRC.REMAIN_QTY`

Pero no se sincronizó el resumen de actividad en `TASK`, específicamente:
- `ACT_WORK_QTY`
- `REMAIN_WORK_QTY`
- `TARGET_WORK_QTY`

P6 estaba leyendo esos campos resumen a nivel actividad.

### Solución aplicada
Sincronizar `TASK` contra la suma de `TASKRSRC` para actividades activas/completas:
- `ACT_WORK_QTY = SUM(TASKRSRC.ACT_REG_QTY)`
- `REMAIN_WORK_QTY = SUM(TASKRSRC.REMAIN_QTY)`
- `TARGET_WORK_QTY = SUM(TASKRSRC.TARGET_QTY)`

### Regla final
**Nunca cerrar o avanzar actividades tocando solo `TASKRSRC`; también hay que sincronizar `TASK`.**

---

## Error 2 — Actividades al 100% con At Complete Labor Cost inflado
### Síntoma
Actividades cerradas mostraban:
- Budgeted Labor Cost correcto
- Actual Labor Cost incorrecto o en 0
- At Complete Labor Cost mayor al budget

### Ejemplo
- `A3250`: budget 9, at complete 18

### Causa raíz
Se actualizaron HH, pero no se sincronizaron correctamente los costos en `TASKRSRC`:
- `ACT_REG_COST`
- `REMAIN_COST`

Quedó `REMAIN_COST` residual, lo que infló el at-complete.

### Solución aplicada
Para actividades cerradas al 100%:
- `ACT_REG_COST = TARGET_COST`
- `REMAIN_COST = 0`

### Regla final
**Al cerrar al 100%, hay que sincronizar HH y costos.**

---

## Error 3 — Fechas desde Excel sin hora se cargaron como `00:00`
### Síntoma
Varias actividades quedaron con:
- `ACT_START_DATE = 00:00`
- `ACT_END_DATE = 00:00`
- mismo día

Resultado visible:
- duración actual = 0

### Ejemplos
- `A2880`
- `A3030`
- `A3040`
- `A3200`
- `A3250`

### Causa raíz
El Excel traía fechas sin componente horaria y se interpretaron literalmente como medianoche.

### Solución aplicada
Si usuario indica inicio y fin el mismo día, interpretarlo como **jornada real**, no como `00:00` a `00:00`.

En la corrección aplicada se usó:
- `08:00` a `18:00`
como jornada estándar de trabajo para las actividades afectadas por la prueba.

### Regla final
**Una fecha sin hora no debe cargarse como medianoche si la intención es una jornada de trabajo.**

---

## Error 4 — Ambigüedad al interpretar filas parciales desde Excel
### Síntoma
En el Excel había filas con:
- `% avance a cargar`
- fecha inicio sí / fecha término no
- o marcas ambiguas de cierre

### Causa raíz
El archivo de captura mezcló:
- actividades a cerrar al 100%
- actividades con avance parcial
- filas aún no completadas por el usuario

### Solución aplicada
Para la prueba se cargaron **solo filas no ambiguas**, es decir, aquellas con:
- `%`
- inicio real
- término real

### Regla final
**No cargar filas ambiguas en pruebas parciales. Separar claramente cierres 100% de avances parciales.**

---

## Error 5 — Riesgo de desalineación por calendario
### Síntoma observado / riesgo detectado
Si una actividad usa un calendario incompatible con la fecha real ingresada, P6 puede reflejar mal:
- duración actual
- lógica de trabajo
- cierre real

### Causa raíz
No basta con cargar una fecha; esa fecha debe ser compatible con `TASK.CLNDR_ID`.

### Hallazgo de la prueba
El programa de prueba usa mezcla de calendarios:
- `7475 | Maestranza #`
- `7509 | Maestranza Full`
- `7476 | Maestranza Sab.`

### Regla final
**Antes de grabar fechas reales, validar el calendario de la actividad. Si no es compatible, cambiar calendario o ajustar la lógica horaria.**

---

## Error 6 — Tratar `% avance` como si siempre fuera Units % Complete
### Síntoma / riesgo
Podría cargarse un `%` de forma coherente en HH, pero incoherente con la lógica del proyecto.

### Hallazgo de la prueba
El proyecto y sus actividades operan con:
- `COMPLETE_PCT_TYPE = CP_Drtn`

### Implicancia
No se debe aplicar ciegamente la lógica:
- `60% avance = 40% remanente`
como si el porcentaje visible del proyecto fuera siempre de unidades.

### Regla final
**Primero validar `COMPLETE_PCT_TYPE` del proyecto/actividad y luego decidir cómo cargar avance, HH y fechas.**

---

## Reglas operativas consolidadas

### Para cierre al 100%
1. validar `% Complete Type`
2. validar calendario
3. definir inicio real y fin real compatibles con jornada/calendario
4. actualizar `TASKRSRC`
   - `ACT_REG_QTY = TARGET_QTY`
   - `REMAIN_QTY = 0`
   - `ACT_REG_COST = TARGET_COST`
   - `REMAIN_COST = 0`
5. actualizar `TASK`
   - `STATUS_CODE = TK_Complete`
   - `ACT_START_DATE`
   - `ACT_END_DATE`
   - `ACT_WORK_QTY`
   - `REMAIN_WORK_QTY`
   - `TARGET_WORK_QTY`
6. verificar en P6

### Para avance parcial
1. validar `% Complete Type`
2. validar calendario
3. definir inicio real si aún no existe
4. actualizar HH y remanente de forma coherente
5. dejar `STATUS_CODE = TK_Active`
6. no asignar fin real si no corresponde
7. sincronizar resumen de `TASK`
8. verificar en P6

---

## Secuencia recomendada para próximas cargas
1. respaldo DB
2. fijar data date
3. revisar baseline
4. revisar `% Complete Type`
5. revisar calendario por actividad
6. preparar archivo de captura sin ambigüedades
7. aplicar carga en `TASKRSRC`
8. sincronizar `TASK`
9. sincronizar costos
10. validar en P6 con actividades testigo

---

## Resultado de la sesión
La campaña de prueba fue útil y validó que la operatividad del agente para P6 debe considerar explícitamente:
- HH por asignación
- resumen visible en actividad
- costos
- calendario
- horas reales
- tipo de porcentaje

Queda pendiente formalizar esto en un **script reusable de carga segura desde Excel hacia DB P6** dentro del proyecto `P6-Standalone-Automation`.
