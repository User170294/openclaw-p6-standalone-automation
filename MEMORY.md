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
