# MEMORY — OT-1844

## ⚠️ Protocolo de sesión
**Antes de responder cualquier consulta de este proyecto, leer:**
→ `projects/OT-1844/README.md` (protocolo completo de consulta, criterios técnicos y estructura del repositorio)

## Resumen vivo del proyecto

### Identificación
- OT: 1844
- PO: 4519143302
- ID: 1425
- Nombre: Fabricación Bandejas Agua Lavado Celda

### Estado actual
- Proyecto en ejecución.
- Repositorio de trazabilidad activo (correos, documentos, cronograma y bitácora).

### Decisiones clave
- 2026-02-22: Método oficial para buscar correos OT-1844 en OWA por categorías:
  - `category:"OT 1844 Recibidos"`
  - `category:"OT 1844 Enviados"`
- 2026-02-22: Alcance operativo SIMTEXX = **10 sistemas** (los otros 5 fueron ejecutados por otra empresa).
- 2026-02-22: Cambio técnico vigente = estructura **A36 + esquema de pintura A3**, sin galvanizado para el alcance actual.
- 2026-02-22: **Criterio oficial de avance semanal** = curva S de P6 por **Planned Value Labor Units (HH time-phased)**.
  - No usar porcentaje por calendario lineal como referencia principal.
  - Semana 8 (W08 = 16–22 feb 2026): valor oficial de referencia = **14,00% acumulado**.
- 2026-02-24: Convención de reporte fijada: usar siempre formato de semana `W##` (W08, W09, W10, ...).

### Próximos hitos
- 09-mar-2026: Entrega 2 bandejas (Hito 1)
- 16-mar-2026: Entrega 2 bandejas (Hito 2)
- 23-mar-2026: Entrega 2 bandejas (Hito 3)
- 30-mar-2026: Entrega 2 bandejas (Hito 4)
- 06-abr-2026: Entrega 2 bandejas (Hito 5)

### 2026-03-03 � Estado RAG validado
- Colecci�n sem�ntica OT-1844 reconstruida y operativa (`ot_1844`, 2160 chunks).
- Comando de reconstrucci�n validado: `python scripts/embed_chunks.py --chunks .\\data\\ot-1844_chunks.jsonl --project OT-1844 --reset`.
- Nota operativa: para �estado actual� preferir consulta compuesta o filtros por tags para evitar sesgo a compras.

### 2026-03-11 — referencia cruzada para foco en programa
- Si el trabajo de foco en OT-1844 involucra P6 / DB / carga de avances / HH / costos / calendarios / `% Complete Type`, revisar antes:
  - `projects/P6-Standalone-Automation/docs/DB_LOAD_TEST_LEARNINGS_OT1844_2026-03-11.md`
- Ese documento contiene el aprendizaje operativo consolidado de las pruebas reales de carga directa en SQLite P6 para no repetir errores de sincronización `TASKRSRC`→`TASK`, costos remanentes, fechas `00:00`, calendarios y cierres ambiguos.
