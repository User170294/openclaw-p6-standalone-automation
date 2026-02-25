# FOCUS LOG — Registro de Ejecución de Foco en Proyectos

**Propósito**: Rastrear cada activación del procedimiento de foco para verificar cumplimiento del protocolo y detectar patrones de fallo.

---

## Formato de entrada

```markdown
## [FECHA HORA UTC-3] — Foco en [PROYECTO]
- Trigger: [frase exacta del usuario]
- Modelo: [modelo activo en la sesión]
- Archivos leídos: [lista con ✅/❌]
- RAG ejecutada: [sí/no] → [N chunks, top score]
- Brechas detectadas: [lista corta]
- Propuesta entregada: [siguiente paso sugerido al usuario]
- Cumplimiento protocolo: [✅ completo / ⚠️ parcial / ❌ fallido]
```

---

## Historial

## [2026-02-25 13:46 UTC-3] — Foco en OT-1844
- Trigger: "activa foco en OT-1844"
- Modelo: anthropic/claude-sonnet-4-5
- Archivos leídos:
  - ✅ projects/OT-1844/README.md
  - ✅ projects/OT-1844/MEMORY.md
  - ✅ projects/OT-1844/LOG.md
  - ✅ projects/OT-1844/INDEX.csv
  - ❌ workspace/memory/ot-1844.md (no existe, esperado en projects/)
- RAG ejecutada: ✅ sí → 1.203 chunks en colección `ot_1844`, top score 0.646 (RFI-011840)
- Brechas detectadas:
  - Script tmp_week9_est.py con error de encoding en ruta XER
  - Archivo memory/ot-1844.md ausente (estructura esperada vs real)
- Propuesta entregada: Corregir ruta XER / revisar RFI específica / resumen completo hilos
- Cumplimiento protocolo: ✅ completo

---

## [2026-02-25 15:19 UTC-3] — Foco en 1844
- Trigger: "hola quiero que hagamos foco en el proyecto 1844"
- Modelo: openai-codex/gpt-5.3-codex
- Archivos leídos:
  - ❌ projects/1844/README.md (no existe)
  - ❌ projects/1844/MEMORY.md (no existe)
  - ❌ projects/1844/LOG.md (no existe)
  - ❌ projects/1844/INDEX.csv (no existe)
  - ✅ projects/OT-1844/README.md (ruta real detectada)
  - ✅ projects/OT-1844/MEMORY.md (ruta real detectada)
  - ✅ projects/OT-1844/LOG.md (ruta real detectada)
  - ✅ projects/OT-1844/INDEX.csv (ruta real detectada)
- RAG ejecutada: ❌ no → colección `data/chroma/ot_1844` no encontrada
- Brechas detectadas:
  - Mismatch de ruta solicitada (`projects/1844`) vs ruta real (`projects/OT-1844`)
  - Colección ChromaDB no visible en `data/chroma/ot_1844`
- Propuesta entregada: Reindexar colección RAG de OT-1844 desde `data/ot-1844_chunks.jsonl`
- Cumplimiento protocolo: ⚠️ parcial (lectura y consolidación completas; RAG bloqueada por colección ausente)

---

**Nota**: Cada sesión de foco debe registrar su ejecución aquí inmediatamente después de entregar panorama al usuario.
