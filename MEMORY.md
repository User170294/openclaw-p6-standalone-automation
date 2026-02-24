# MEMORY.md — Memoria Permanente

**Última actualización**: 2026-02-22

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

### RAG Semántico de Proyectos (activo desde 2026-02-23)
- Stack: sentence-transformers (`paraphrase-multilingual-MiniLM-L12-v2`) + ChromaDB persistente.
- Vector store: `data/chroma/` — colecciones por proyecto (ej. `ot_1844`).
- Scripts: `scripts/embed_chunks.py`, `scripts/search_project.py`, `scripts/foco_proyecto.py`.
- OT-1844 indexada: 2262 chunks desde `data/ot-1844_chunks.jsonl`.
- Regla de activación: al hacer "foco en proyecto", verificar colección ChromaDB y usar RAG automáticamente para consultas técnicas. Citar fuente [DOC_ID pág. N].
- Para nuevos proyectos: correr `embed_chunks.py` con los chunks del proyecto nuevo.
- Siempre pasar `PYTHONUTF8=1` al ejecutar los scripts en Windows.
- Convención oficial de semana calendario para OT-1844: W08 = 2026-02-16 a 2026-02-22; luego consecutivo (W09, W10, ...). Usar formato `W##` en todos los reportes.

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
