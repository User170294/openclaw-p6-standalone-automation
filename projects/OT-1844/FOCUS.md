# FOCUS — OT-1844

## Estado actual
Proyecto en ejecución con repositorio de trazabilidad activo, RAG operativo y criterio oficial de avance basado en curva S HH de P6.

## Datos clave
- OT interna: `1844`
- PO cliente: `4519143302`
- ID licitación: `1425`
- Cliente: Minera Spence S.A. (BHP)
- Estado: en ejecución
- Alcance SIMTEXX: 10 sistemas de lavado
- Materiales/criterios base:
  - estructura: A36
  - tratamiento estructura: esquema de pintura A3, sin galvanizado
  - bandejas: SS316L
  - soldadura de referencia: AWS D1.1
- Cronograma oficial:
  - XER activo: `docs/schedule/SPC-2220-PS-PMS-011840_Fabricación Bandejas Agua Lavado Celdas OT 1844_Rev.B.xer`
  - BAC de referencia: `8100 HH`
  - W08: `1134 HH` = `14,00%`
  - W09: `2295 HH` = `28,33%`
- Hitos de entrega:
  - 09-mar-2026
  - 16-mar-2026
  - 23-mar-2026
  - 30-mar-2026
  - 06-abr-2026 (crítico)
- RAG validado: colección `ot_1844` operativa; README reporta corpus 2200+ chunks y MEMORY/LOG registran reconstrucción operativa validada.
- Correos: filtrar por categorías OWA `OT 1844 Recibidos` y `OT 1844 Enviados`.

## Decisiones técnicas vigentes
- Método oficial de avance semanal: Planned Value Labor Units (HH) time-phased desde cronograma P6; no usar % lineal por calendario ni conteo simple de actividades.
- Convención de reporte semanal: usar siempre formato `W##`.
- Para consultas técnicas, priorizar chunks por tags temáticos; si no basta, ir a `docs/summaries/` y luego PDF original.
- Respuestas técnicas con fuente explícita cuando aplique.
- Si el trabajo involucra P6/DB/carga de avances/HH/costos/calendarios/% Complete Type, revisar referencia cruzada en `projects/P6-Standalone-Automation/docs/DB_LOAD_TEST_LEARNINGS_OT1844_2026-03-11.md`.
- No renegociar sin confirmación del usuario: alcance de 10 sistemas, A36 + pintura A3, sin galvanizado.

## Brechas pendientes (priorizadas)
1. Mantener consistencia entre trazabilidad documental, cronograma P6 y consultas de avance semanal.
2. Confirmar color RAL definitivo de estructura (pendiente entre RAL 7035 y RAL 5017; ver RFI-011843).
3. Evitar sesgo de consultas RAG genéricas; usar query compuesta o tags cuando se busque estado global.
4. Reforzar referencia cruzada con aprendizajes P6 cuando el trabajo toque DB/cargas/HH.
5. Seguir consolidando correo/Teams/documentos con trazabilidad completa por fuente.

## Instrucción de arranque para Lilit
1. Leer primero `README.md`; ese archivo manda sobre el protocolo de consulta del proyecto.
2. Luego leer `MEMORY.md`, `LOG.md`, `INDEX.csv` y, si aplica, `MAIL_LOG.md` / `TEAMS_LOG.md`.
3. Si la pregunta es técnica, buscar primero en RAG usando tags del tema.
4. Si la pregunta es de cronograma/avance/actividades, responder con la jerarquía Entrega → WBS → Actividad y con criterio oficial HH time-phased.
5. Si el trabajo toca P6/SQLite/XER/carga de avances, revisar antes los aprendizajes de `P6-Standalone-Automation` para no repetir errores operativos.
