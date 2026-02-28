# MEMORY.md - Memoria Permanente

**Última actualización**: 2026-02-28

## 🎯 Información Crítica

### Contexto general
- **Usuario**: Edgardo
- **Zona horaria**: UTC-3 (Santiago, Chile)
- **Idioma preferido**: Español
- **Lenguaje favorito**: Python

### Configuración técnica
- **Modelo activo**: openai-codex/gpt-5.3-codex (ChatGPT Plus OAuth)
- **Workspace**: `C:\Users\josej\.openclaw\workspace`
- **Canal principal**: Telegram

### Decisiones importantes
- Mantener GPT Codex 5.3 como modelo principal.
- Priorizar memoria persistente en `MEMORY.md`, `memory/*.md` y `.learnings/*.md`.

### Decisiones operativas vigentes
- OT 1844 (interna) equivale a PO 4519143302 (cliente) e ID 1425 (licitación).
- Para correo personal, priorizar Microsoft Graph API sobre navegador/OWA cuando sea posible.
- Configuración de browser OpenClaw establecida con `browser.profiles.openclaw.cdpPort: 18810` (18800 ocupado).
- Outlook Notes: para crear notas persistentes en OWA usar creación de nota nueva + tipeo real en editor Draft.js; evitar manipulación DOM directa para escribir contenido.
- Política de cierre de sesión: guardar solo señal útil (decisiones, pendientes reales, cambios) en `memory/YYYY-MM-DD.md`, sin disparadores por tiempo fijo.
- Al cerrar sesión, mostrar confirmación verificable del guardado (ruta + bloque guardado).
- Para OT-1844, cuando se pida "resumen", entregar formato de informe detallado (hilos + contexto + pendientes + riesgos), no solo resumen ejecutivo.
- **Procedimiento de foco en proyectos** (2026-02-25): protocolo imperativo reforzado en `AGENTS.md` — PROHIBIDO responder al trigger de foco sin ejecutar checklist completo de lectura + RAG + consolidación. Registrar cada activación en `memory/focus-log.md`.
- **Normalización de rutas OT-1844** (2026-02-25): se eliminó alias `projects/1844` (junction) y se mantiene `projects/OT-1844` como ruta canónica para evitar ambigüedad y fallos por rutas mixtas.

### RAG Semántico de Proyectos (activo desde 2026-02-23)
- Stack: sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`) + ChromaDB persistente.
- Vector store: `data/chroma/` - colecciones por proyecto (ej. `ot_1844`).
- Scripts: `scripts/embed_chunks.py`, `scripts/search_project.py`, `scripts/foco_proyecto.py`.
- OT-1844 indexada: 2262 chunks desde `data/ot-1844_chunks.jsonl`.
- Regla de activación: al hacer "foco en proyecto", verificar colección ChromaDB y usar RAG automáticamente para consultas técnicas. Citar fuente [DOC_ID pág. N].
- Para nuevos proyectos: correr `embed_chunks.py` con los chunks del proyecto nuevo.
- Retrieval de RAG actualizado a modo híbrido (vector + BM25 con fusión RRF) en `search_project.py` y `foco_proyecto.py`.
- Benchmark operativo en `scripts/rag_ab_test.py` con métricas `avg_rerank` y `rel@3` por query.
- Siempre pasar `PYTHONUTF8=1` al ejecutar los scripts en Windows.
- Convención oficial de semana calendario para OT-1844: W08 = 2026-02-16 a 2026-02-22; luego consecutivo (W09, W10, ...). Usar formato `W##` en todos los reportes.
- OT-1844 RAG (2026-02-26): se retaggearon chunks (`data/ot-1844_chunks.jsonl`), se reindexó colección `ot_1844` (1203 chunks), y `scripts/search_project.py` quedó corregido con filtro de tags robusto por metadata (evita falsos "sin resultados" con `--tags`).
- P6 Standalone (2026-02-26): cambios de recursos para OT 1844 se ejecutan primero en BD WORK clonada; no sobre BD principal sin validación.
- P6 OT 1844_B (PROJ_ID 26196, 2026-02-26): se implementó reasignación por cuadrillas OP1/OP2/OP3 por WBS nivel 3 (153937, 153962, 153970, 153978, 153986) manteniendo HH.
- P6 OT 1844_B (PROJ_ID 26196, 2026-02-27): proyecto eliminado de la DB SQLite principal por instrucción del usuario, con backup previo (`...Rev B.BACKUP_20260227_163242.db`) y verificación `PROJECT_LEFT=0`.
- Regla técnica P6 (2026-02-26): al crear/reasignar recursos en SQLite, asegurar `RSRC.RSRC_TYPE` y `TASKRSRC.RSRC_TYPE` en `RT_Labor` para que P6 los trate como HH/labor y no material.
- Criterio oficial de control semanal P6 OT-1844 (2026-02-27): calcular y reportar avance/proyección con curva S de Labor Units time-phased en días laborales (L-V), alineado con Activity Usage Profile (Baseline + Planned Value Labor Units). No usar corte simple por `TARGET_END_DATE` para programas de trabajo.
- Lección aprendida P6 forecast (2026-02-28): para reportes semanales, tomar Forecast desde la lógica P6 (`Actual + Remaining Early` time-phased) y no mezclar métodos ni distribuir linealmente desde TASK/TASKRSRC cuando se busque reproducir la curva del cliente en P6.
- Criterio validado por usuario (2026-02-28): proyección/valor planificado semanal se calcula con curva S time-phased semanal (semana ISO lunes-domingo), distribuyendo HH de actividades en días laborales y luego agregando por semana; usar `% semana` y `% acumulado` sobre BAC total.

## 📚 Qué recordar
- Decisiones importantes y cambios de estado
- Lecciones aprendidas y soluciones efectivas
- Contexto de proyectos en curso
- Preferencias del usuario

## 🧹 Qué descartar
- Conversaciones rutinarias sin valor
- Detalles superficiales
- Confirmaciones repetidas
- Ruido contextual

## 🔄 Compaction
- Trigger: cuando el contexto alcance ~40,000 tokens
- Acción: destilar sesión a `memory/YYYY-MM-DD.md`
- Criterio: solo datos críticos, sin relleno

## 📌 Referencias
- OpenClaw docs: https://docs.openclaw.ai
- GitHub: https://github.com/openclaw/openclaw
