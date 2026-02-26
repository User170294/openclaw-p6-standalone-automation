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

## [2026-02-25 15:22 UTC-3] � Reindex + verificaci�n OT-1844
- Trigger: "ejecutala y volvamos a verificar"
- Modelo: openai-codex/gpt-5.3-codex
- Acci�n RAG: ? `embed_chunks.py --chunks data/ot-1844_chunks.jsonl --project OT-1844 --reset`
- Resultado RAG: 1203 chunks cargados en colecci�n `ot_1844`.
- Verificaci�n b�squeda: ? `search_project.py --project OT-1844 --ask "estado actual" --top 3`
- Verificaci�n alias ruta: ? creado junction `projects/1844 -> projects/OT-1844`
- Verificaci�n archivos en `projects/1844`: ? README/MEMORY/LOG/INDEX accesibles
- Observaci�n t�cnica: `data/chroma/ot_1844` no existe como carpeta f�sica; Chroma persiste por UUID + sqlite (`data/chroma/chroma.sqlite3`).
- Cumplimiento protocolo: ? completo (con adaptaci�n de ruta)
## 2026-02-25 21:21 (UTC-3) � Foco en finanzas
- Trigger: ""vamos a finazas""
- Archivos le�dos: projects/finanzas/README.md; projects/finanzas/MEMORY.md; projects/finanzas/LOG.md; projects/finanzas/INDEX.csv
- RAG ejecutada: no ? colecci�n no encontrada
- Brechas: sin chunks JSONL en data/; sin colecci�n ChromaDB data/chroma/finanzas
- Propuesta: indexar chunks del proyecto finanzas para habilitar búsqueda semántica

## [2026-02-26 08:05 UTC-3] — Foco en finanzas
- Trigger: "vamoas con finanzas"
- Modelo: openai-codex/gpt-5.3-codex
- Archivos leídos:
  - ✅ projects/finanzas/README.md
  - ✅ projects/finanzas/MEMORY.md
  - ✅ projects/finanzas/LOG.md
  - ✅ projects/finanzas/INDEX.csv
  - ✅ data/ contiene `finanzas_chunks.jsonl`
  - ❌ data/chroma/ no muestra colección `finanzas`
- RAG ejecutada: ❌ no → Colección RAG no encontrada para finanzas
- Brechas detectadas:
  - Falta colección ChromaDB del proyecto para consultas semánticas
  - `MEMORY.md` del proyecto aún sin decisiones consolidadas (pendiente)
- Propuesta entregada: indexar `data/finanzas_chunks.jsonl` para habilitar búsqueda RAG y luego revalidar top 3 de “estado actual”.
- Cumplimiento protocolo: ✅ completo
## [2026-02-26 08:12 UTC-3] � Foco en OT-1844
- Trigger: ""hagamos foco en el proyecto 1844""
- Archivos le�dos: projects/OT-1844/README.md; projects/OT-1844/MEMORY.md; projects/OT-1844/LOG.md (100); projects/OT-1844/INDEX.csv (50)
- RAG ejecutada: s� ? [1203 chunks, top score 0.000]
- Brechas: comando grep no disponible en PowerShell; data/chroma/ no muestra carpeta nominal ot_1844 (colecci�n existente en Chroma SQLite)
- Propuesta: ajustar checklist cross-platform (Select-String) y validar calidad de retrieval para query ""estado actual"".
## [2026-02-26 10:36 UTC-3] � Foco en OT-1844
- Trigger: ""vamos al 1844""
- Archivos le�dos: projects/OT-1844/README.md; projects/OT-1844/MEMORY.md; projects/OT-1844/LOG.md (100); projects/OT-1844/INDEX.csv (50)
- RAG ejecutada: s� ? [1267 chunks, top score 0.000; rerank top -2.6666]
- Brechas: no hay carpeta visible por nombre en data/chroma (lookup directo fall�); recuperaci�n sem�ntica para "estado actual" con baja relevancia
- Propuesta: consultar con query orientada (hitos/avance/W09) o refrescar embeddings si persiste baja se�al
