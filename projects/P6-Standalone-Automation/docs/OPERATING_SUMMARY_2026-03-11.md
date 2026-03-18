# Operating Summary — P6-Standalone-Automation — 2026-03-11

## Qué es este proyecto

`P6-Standalone-Automation` centraliza automatizaciones y criterios operativos para trabajar con **Primavera P6 Professional Standalone**, principalmente sobre:

- **DB SQLite de P6**,
- **archivos XER**,
- validaciones de cronograma,
- reportes semanales,
- cambios controlados con respaldo y trazabilidad.

El proyecto está activo y ya tiene aprendizaje técnico validado en terreno de prueba.

---

## Objetivo operativo actual

Dejar una base reusable para tres líneas de trabajo:

1. **inspección y auditoría** del programa,
2. **comparación técnica entre XER y DB**,
3. **carga o mutación segura** sobre XER/DB sin romper la lectura de P6.

---

## Estado actual real

## Lo que ya está resuelto

### 1) Auditoría inicial SQLite
Ya existe capacidad de:
- listar estructura relevante,
- inspeccionar tablas P6,
- detectar actividades sin predecesora,
- detectar hitos vencidos,
- generar salidas CSV/MD.

### 2) Mutación segura de XER
Ya existe una base funcional para:
- editar XER por parche de líneas,
- preservar `ERMHDR` y `%E`,
- evitar corrupción por reserialización completa,
- aplicar cambios controlados sobre `TASKRSRC`.

### 3) Reasignación de recursos en DB
Ya se validó en SQLite un flujo de:
- creación de nuevos recursos,
- split de asignaciones,
- conservación de HH objetivo,
- ajuste posterior de tasas temporales (`TARGET_QTY_PER_HR`, `REMAIN_QTY_PER_HR`).

### 4) Método operativo para PV/EV semanal
El proyecto ya acumuló aprendizaje validado para:
- curvas semanales,
- BAC / EV / ETC / EAC,
- diferencias entre lógica simple y lectura real de P6,
- necesidad de distinguir modo `logic` vs `p6_visual`.

### 5) Aprendizaje fuerte de carga DB directa
Quedó validado que para cargar avance en SQLite P6 **no basta tocar `TASKRSRC`**.

También deben sincronizarse, según el caso:
- resumen laboral visible en `TASK`,
- costos reales/remanentes,
- fechas reales compatibles con calendario,
- `% Complete Type` del proyecto/actividad.

---

## Reglas técnicas vigentes

## A. XER
- No reserializar el archivo completo si no es estrictamente necesario.
- Preferir parche incremental por líneas.
- Validar siempre preservación de cabecera `ERMHDR`, cierre `%E` y HH objetivo labor.

## B. DB SQLite P6
- Toda mutación con respaldo previo.
- Validar `NEXTKEY` cuando se creen registros.
- Si se actualiza avance, sincronizar también campos resumen de `TASK` que la UI de P6 consume.
- En cierres al 100%, sincronizar también costos para evitar `At Complete` inflado.

## C. Reportabilidad semanal
- No asumir que una aproximación simple L-V sirve para todos los programas.
- Cuando el objetivo es reproducir lectura real de P6, considerar:
  - calendario de actividad,
  - excepciones,
  - horas efectivas de solape,
  - diferencia entre lógica de trabajo y bucket visual.

---

## Brechas actuales

### 1) Comparador reusable XER vs DB
Existe evidencia y pruebas puntuales, pero falta una herramienta estable y parametrizable.

### 2) Resumen operativo vivo indexado
La RAG del proyecto responde, pero para la consulta “estado actual” recupera sobre todo el PDF de estándar de scheduling, no el estado operativo real.

### 3) Carpeta `scripts/` con ruido alto
Hay demasiados `tmp_*` mezclados con scripts útiles. Eso entorpece mantenimiento y recuperación semántica.

### 4) Falta script reusable de carga segura Excel → DB
El método ya está aprendido, pero aún no quedó formalizado como herramienta única y robusta.

---

## Artefactos más valiosos hoy

- `docs/XER_DB_VALIDATION_FLOW.md`
- `docs/DB_LOAD_TEST_LEARNINGS_OT1844_2026-03-11.md`
- `docs/SCRIPT_AUDIT_2026-03-11.md`
- `scripts/pilot_audit.py`
- `scripts/xer_update.py`
- `scripts/replace_resource_with_three_ops.py`
- `scripts/fix_op_rate_spread.py`

---

## Prioridad recomendada

1. Consolidar **comparador XER vs DB**.
2. Indexar este resumen operativo para mejorar recuperación semántica.
3. Separar scripts productivos de temporales.
4. Formalizar cargador seguro Excel → DB.

---

## Lectura corta del proyecto

Este proyecto ya no está en fase de prueba conceptual.

Está en fase de **consolidación operativa**:
- lo crítico ya se aprendió,
- lo que falta es empaquetarlo bien,
- y dejar una ruta única, reusable y segura para trabajar con P6 Standalone.
