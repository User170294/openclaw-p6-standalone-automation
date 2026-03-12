## [2026-02-27 17:02 UTC-3] â€” Foco en P6
- Trigger: "hagamos foco en el proyecto P6"
- Archivos leÃ­dos: projects/P6/README.md (no encontrado), projects/P6/MEMORY.md (no encontrado), projects/P6/LOG.md (no encontrado), projects/P6/INDEX.csv (no encontrado)
- RAG ejecutada: no â†’ colecciÃ³n no encontrada (`data/chroma/p6`)
- Brechas: estructura de proyecto inexistente en `projects/P6`; sin chunks detectados en `data/`; sin colecciÃ³n ChromaDB
- Propuesta: crear estructura base del proyecto P6 y luego indexar chunks para habilitar RAG
## [2026-02-27 17:03 UTC-3] ï¿½ Foco en P6-Standalone-Automation
- Trigger: ""vamos con foco al proyecto P6-Standalone-Automation""
- Archivos leï¿½dos: projects/P6-Standalone-Automation/README.md, MEMORY.md, LOG.md, INDEX.csv
- RAG ejecutada: no ? colecciï¿½n no encontrada (data/chroma/p6_standalone_automation)
- Brechas: sin chunks detectados del proyecto en data/; sin colecciï¿½n ChromaDB
- Propuesta: generar/ubicar chunks del proyecto e indexar colecciï¿½n para habilitar consultas semï¿½nticas
## [2026-02-28 14:03 UTC-3] ï¿½ Foco en P6-Standalone-Automation
- Trigger: hagamos foco en P6-Standalone-Automation
- Archivos leï¿½dos: projects/P6-Standalone-Automation/README.md; projects/P6-Standalone-Automation/MEMORY.md; projects/P6-Standalone-Automation/LOG.md; projects/P6-Standalone-Automation/INDEX.csv
- RAG ejecutada: no ? colecciï¿½n no encontrada
- Brechas: sin chunks JSONL del proyecto en data/; sin colecciï¿½n ChromaDB en data/chroma/
- Propuesta: indexar chunks y crear colecciï¿½n RAG del proyecto

## [2026-02-28 14:43 UTC-3] â€” Foco en P6-Standalone-Automation
- Trigger: "hagamos foco en P6-Standalone-Automation"
- Archivos leÃ­dos: projects/P6-Standalone-Automation/README.md; projects/P6-Standalone-Automation/MEMORY.md; projects/P6-Standalone-Automation/LOG.md (100 lÃ­neas); projects/P6-Standalone-Automation/INDEX.csv (50 lÃ­neas)
- RAG ejecutada: no â†’ colecciÃ³n no encontrada (`data/chroma/p6_standalone_automation`)
- Brechas: ruta de colecciÃ³n no existe aunque LOG registra indexaciÃ³n previa; posible divergencia entre nombre lÃ³gico de colecciÃ³n y directorio fÃ­sico UUID en Chroma
- Propuesta: reindexar/validar colecciÃ³n `p6_standalone_automation` y luego correr bÃºsqueda "estado actual"
## [2026-02-28 21:24 UTC-3] ï¿½ Foco en OT-1844
- Trigger: "vamos con el OT-1844"
- Archivos leï¿½dos: projects/OT-1844/README.md; projects/OT-1844/MEMORY.md; projects/OT-1844/LOG.md (100 lï¿½neas); projects/OT-1844/INDEX.csv (50 lï¿½neas)
- RAG ejecutada: sï¿½ ? 2160 chunks, top score 0.7512
- Brechas: no existe carpeta explï¿½cita `data/chroma/ot_1844` (backend usa directorios UUID + `chroma.sqlite3`); consulta funcional validada vï¿½a `search_project.py`
- Propuesta: continuar con consulta especï¿½fica (cronograma, RFIs, compras o avances W##) usando RAG hï¿½brido con citas
## [2026-02-28 21:42 UTC-3] ï¿½ Foco en P6-Standalone-Automation
- Trigger: "hagamos foco en un proyecto" + selecciï¿½n "P6-Standalone-Automation"
- Archivos leï¿½dos: projects/P6-Standalone-Automation/README.md, MEMORY.md, LOG.md, INDEX.csv; data/* (filtro p6-standalone-automation); data/chroma/* (filtro p6_standalone_automation)
- RAG ejecutada: sï¿½ ? 400 chunks, top score 0.345
- Brechas: inconsistencia en verificaciï¿½n de colecciï¿½n por carpeta en data/chroma; seï¿½ales dï¿½biles en consulta "estado actual" (scores < 0.5)
- Propuesta: reindexar/verificar persistencia Chroma y usar consulta temï¿½tica mï¿½s especï¿½fica para obtener evidencia tï¿½cnica ï¿½til
## [2026-02-28 22:17 UTC-3] ï¿½ Foco en P6-Standalone-Automation
- Trigger: "P6-Standalone-Automation"
- Archivos leï¿½dos: projects/P6-Standalone-Automation/README.md, projects/P6-Standalone-Automation/MEMORY.md, projects/P6-Standalone-Automation/LOG.md, projects/P6-Standalone-Automation/INDEX.csv
- RAG ejecutada: sï¿½ ? [400 chunks, top score 0.345]
- Brechas: [No se detecta carpeta data/chroma/p6_standalone_automation por nombre; colecciï¿½n existe en ChromaDB por UUID/metadata]
- Propuesta: Definir y ejecutar rutina piloto con criterios de ï¿½xito y umbral de calidad de retrieval para consultas "estado".
## [2026-03-02 10:17 UTC-3] ï¿½ Foco en OT-1844
- Trigger: "OT-1844"
- Archivos leï¿½dos: projects/OT-1844/README.md; projects/OT-1844/MEMORY.md; projects/OT-1844/LOG.md (100); projects/OT-1844/INDEX.csv (50); data/* (grep OT-1844); data/chroma/* (grep ot_1844)
- RAG ejecutada: sï¿½ ? 2160 chunks, top score rerank=0.7512
- Brechas: data/chroma sin carpeta legible ot_1844 (usa UUID); query "estado actual" sesgada a compras (score vector 0.000)
- Propuesta: fijar query de estado combinada (hitos+avance+riesgos) y validar mapeo colecciï¿½n?nombre para diagnï¿½stico mï¿½s claro.
## [2026-03-03 14:18 UTC-3] ï¿½ Foco en OT-1844
- Trigger: "OT-1844"
- Archivos leï¿½dos: projects/OT-1844/README.md; projects/OT-1844/MEMORY.md; projects/OT-1844/LOG.md (100 lï¿½neas); projects/OT-1844/INDEX.csv (50 lï¿½neas); data/* (filtro ot-1844); data/chroma/* (filtro ot_1844)
- RAG ejecutada: no ? colecciï¿½n no encontrada (`data/chroma/ot_1844` inexistente)
- Brechas: sin colecciï¿½n ChromaDB visible para OT-1844 en ruta esperada; RAG semï¿½ntico no ejecutable bajo protocolo actual
- Propuesta: indexar ahora los chunks OT-1844 para crear colecciï¿½n y habilitar bï¿½squeda de estado actual
## [2026-03-03 14:19 UTC-3] ï¿½ Foco en OT-1844
- Trigger: "OT-1844"
- Archivos leï¿½dos: projects/OT-1844/README.md; projects/OT-1844/MEMORY.md; projects/OT-1844/LOG.md (100 lï¿½neas); projects/OT-1844/INDEX.csv (50 lï¿½neas); data/* (filtro ot-1844); data/chroma/* (filtro ot_1844)
- RAG ejecutada: sï¿½ ? 2160 chunks, top rerank 0.7512 (query: "estado actual")
- Brechas: la query "estado actual" recupera principalmente compras (baja diversidad temï¿½tica)
- Propuesta: para panorama general usar query compuesta (avance + hitos + riesgos + compras) o filtros por tags
## [2026-03-04 11:32 UTC-3] ï¿½ Foco en OT-1844
- Trigger: "OT-1844"
- Archivos leï¿½dos: projects/OT-1844/README.md; projects/OT-1844/MEMORY.md; projects/OT-1844/LOG.md (100 lï¿½neas); projects/OT-1844/INDEX.csv (50 lï¿½neas)
- RAG ejecutada: sï¿½ ? 2160 chunks, top score 0.7512
- Brechas: ruta data/chroma/ot_1844 no existe como carpeta fï¿½sica (backend usa UUIDs); consulta "estado actual" sesga a compras
- Propuesta: usar query compuesta con tags (cronograma+hitos+riesgos+compras) para panorama integral

## [2026-03-05 12:34 UTC-3] â€” Foco en OT-1844
- Trigger: "OT-1844"
- Archivos leÃ­dos: projects/OT-1844/README.md; projects/OT-1844/MEMORY.md; projects/OT-1844/LOG.md (100 lÃ­neas); projects/OT-1844/INDEX.csv (50 lÃ­neas); data/* (filtro 1844); data/chroma/* (filtro ot_1844)
- RAG ejecutada: no â†’ colecciÃ³n no encontrada (`data/chroma/ot_1844`)
- Brechas: no existe carpeta explÃ­cita por nombre de colecciÃ³n en `data/chroma`; validaciÃ³n de estado actual no ejecutada por protocolo
- Propuesta: indexar/revincular colecciÃ³n `ot_1844` y luego correr `search_project.py --ask "estado actual" --top 3`
## [2026-03-06 18:30 UTC-3] ï¿½ Foco en OT-1844
- Trigger: "OT-1844"
- Archivos leï¿½dos: projects/OT-1844/README.md; projects/OT-1844/MEMORY.md; projects/OT-1844/LOG.md (100 lï¿½neas); projects/OT-1844/INDEX.csv (50 lï¿½neas); data/* (filtro 1844); data/chroma/* (filtro ot_1844)
- RAG ejecutada: no ? colecciï¿½n no encontrada (`data/chroma/ot_1844`)
- Brechas: `data/chroma/` usa UUIDs y no expone carpeta nominal `ot_1844`; protocolo actual no permite validar estado sin esa ruta
- Propuesta: ï¿½indexar/revincular colecciï¿½n `ot_1844` y ejecutar bï¿½squeda "estado actual" ahora?
## [2026-03-06 18:32 UTC-3] ï¿½ Foco en OT-1844 (reindex + RAG)
- Trigger: "hazlo" (sobre foco OT-1844)
- Archivos leï¿½dos: projects/OT-1844/README.md; projects/OT-1844/MEMORY.md; projects/OT-1844/LOG.md (100 lï¿½neas); projects/OT-1844/INDEX.csv (50 lï¿½neas); data/*; data/chroma/*
- RAG ejecutada: sï¿½ ? 2160 chunks, top rerank 0.7512
- Brechas: consulta "estado actual" quedï¿½ sesgada a compras (score vector 0.000; rerank alto)
- Propuesta: usar consulta compuesta con tags (cronograma+hitos+riesgos+compras) para panorama integral
## [2026-03-07 12:20 UTC-3] ï¿½ Foco en SOLID_TO_STEEL
- Trigger: "activalo :D"
- Archivos leï¿½dos: projects/solid_to_steel/README.md; projects/solid_to_steel/MEMORY.md; projects/solid_to_steel/LOG.md (100 lï¿½neas); projects/solid_to_steel/INDEX.csv (50 lï¿½neas); data/* (filtro solid_to_steel); data/chroma/* (filtro solid_to_steel)
- RAG ejecutada: no ? colecciï¿½n no encontrada (data/chroma/solid_to_steel)
- Brechas: sin chunks del proyecto detectados en data/; sin colecciï¿½n ChromaDB nominal para solid_to_steel; MEMORY.md y LOG.md aï¿½n con cabecera histï¿½rica "ADVANCE STEEL"
- Propuesta: crear chunks iniciales del proyecto y ejecutar indexaciï¿½n para habilitar RAG; normalizar nombres internos a SOLID_TO_STEEL
## [2026-03-07 14:11 UTC-3] ï¿½ Foco en SOLID_TO_STEEL
- Trigger: "ok vamos con las pruebas, primero hagamos fioco en el proyecto"
- Archivos leï¿½dos: projects/solid_to_steel/README.md; projects/solid_to_steel/MEMORY.md; projects/solid_to_steel/LOG.md; projects/solid_to_steel/INDEX.csv
- RAG ejecutada: no ? colecciï¿½n no encontrada
- Brechas: falta colecciï¿½n ChromaDB data/chroma/solid_to_steel; endpoint /status inestable
- Propuesta: indexar chunks data/solid_to_steel_chunks.jsonl en Chroma y luego correr bï¿½squeda "estado actual"
## [2026-03-09 12:22 UTC-3] ï¿½ Foco en selecciï¿½n de proyecto
- Trigger: "hagamos foco en un proyecto, dime cuales tengo disponible"
- Archivos leï¿½dos: projects/*/README.md; projects/*/MEMORY.md; projects/*/LOG.md (hasta 100); projects/*/INDEX.csv (hasta 50); data/* (filtro por proyecto); data/chroma/* (verificaciï¿½n)
- RAG ejecutada: sï¿½ (OT-1844: 2160 chunks, top rerank 0.7512; FINANZAS: 19 chunks; P6-STANDALONE-AUTOMATION: 400 chunks; SOLID_TO_STEEL: 4 chunks); no para Bodega-Simtexx (colecciï¿½n no encontrada)
- Brechas: Bodega-Simtexx sin chunks/colecciï¿½n; para todos los proyectos la carpeta nominal data/chroma/<proyecto_normalizado> no aparece (backend usa UUID)
- Propuesta: seleccionar proyecto objetivo y continuar foco detallado con consolidaciï¿½n completa
## [2026-03-09 12:28 UTC-3] ï¿½ Foco en OT-1844
- Trigger: "OT-1844"
- Archivos leï¿½dos: projects/OT-1844/README.md; projects/OT-1844/MEMORY.md; projects/OT-1844/LOG.md (100 lï¿½neas); projects/OT-1844/INDEX.csv (50 lï¿½neas); data/ot-1844_chunks.jsonl; data/ot-1844_chunks.bak.jsonl; data/ot-1844_docs.jsonl
- RAG ejecutada: sï¿½ ? 2160 chunks, top score rerank=1.2362 (query: "estado actual del proyecto: avance, hitos, riesgos")
- Brechas: consulta de estado devuelve evidencia tï¿½cnica parcial/no centrada en cronograma (hitos/avance no priorizados en top 3)
- Propuesta: correr segunda bï¿½squeda con tags `cronograma,P6,hitos` y consolidar estado semanal W## con foco en entregas y float crï¿½tico
## [2026-03-09 16:33 UTC-3] ï¿½ Foco en P6-Standalone-Automation
- Trigger: "cambiemos foco al proyecto P6-Standalone-Automation"
- Archivos leï¿½dos: projects/P6-Standalone-Automation/README.md; MEMORY.md; LOG.md (100 lï¿½neas); INDEX.csv (50 lï¿½neas); data/p6-standalone-automation_chunks.jsonl; data/p6-standalone-automation_docs.jsonl
- RAG ejecutada: sï¿½ ? colecciï¿½n `p6_standalone_automation` con 400 chunks; top rerank=-10.8523 (query: "estado actual del proyecto")
- Brechas: consulta de estado actual con baja seï¿½al semï¿½ntica (top 3 genï¿½ricos/glosario); falta documentaciï¿½n especï¿½fica de flujo GitHub para el proyecto
- Propuesta: definir e implementar baseline GitHub (repo, ramas, PR template, changelog y release de reportes) en este proyecto
- Fecha/hora UTC-3: 2026-03-10 08:03
- Trigger: foco en P6-Standalone-Automation
- Archivos leï¿½dos: projects/P6-Standalone-Automation/README.md; MEMORY.md; LOG.md (100); INDEX.csv (50)
- RAG: sï¿½ + 400 chunks + top score rerank=-11.1359
- Brechas: ï¿½ndice CSV inconsistente; colecciï¿½n no detectable por carpeta canï¿½nica data/chroma/p6_standalone_automation (se resuelve vï¿½a metadatos internos); resultados RAG poco especï¿½ficos al estado operativo
- Propuesta: limpiar INDEX.csv, documentar ruta/estado real de colecciï¿½n Chroma y crear resumen operativo propio en docs para mejorar retrieval
## 2026-03-10 16:01 UTC-3
- Trigger: foco en P6-Standalone-Automation
- Archivos leï¿½dos: projects/P6-Standalone-Automation/README.md; projects/P6-Standalone-Automation/MEMORY.md; projects/P6-Standalone-Automation/LOG.md; projects/P6-Standalone-Automation/INDEX.csv
- RAG: sï¿½ + 400 chunks + top score 0.000 (rerank top -11.1390)
- Brechas: INDEX.csv inconsistente; bï¿½squeda RAG de estado devuelve chunks dï¿½biles del PDF estï¿½ndar, falta documentaciï¿½n/resï¿½menes mï¿½s orientados a estado operativo actual.
- Propuesta: crear resumen operativo indexado del proyecto y/o tags mï¿½s especï¿½ficos para mejorar retrieval de estado.
## 2026-03-11 09:41 UTC-3
- Trigger: foco en P6-Standalone-Automation
- Archivos leï¿½dos:
  - projects/P6-Standalone-Automation/README.md
  - projects/P6-Standalone-Automation/MEMORY.md
  - projects/P6-Standalone-Automation/LOG.md (100 lï¿½neas)
  - projects/P6-Standalone-Automation/INDEX.csv (50 lï¿½neas)
  - projects/P6-Standalone-Automation/data/ (verificado)
  - data/chroma/p6_standalone_automation/ (verificado)
- RAG: no; 0 chunks; top score: N/A
- Brechas:
  - Colecciï¿½n RAG no encontrada en data/chroma/p6_standalone_automation
  - No existe data/chroma/p6_standalone_automation dentro de la carpeta del proyecto
- Propuesta:
  - Reindexar la colecciï¿½n RAG del proyecto y luego validar con bï¿½squeda semï¿½ntica top 3
- Fecha/hora UTC-3: 2026-03-11 12:27
- Trigger: OT-1844
- Archivos leï¿½dos: README.md; MEMORY.md; LOG.md; INDEX.csv
- RAG: sï¿½ + 2160 chunks + top score 0.602 (consulta tags cronograma/P6/hitos)
- Brechas: colecciï¿½n no visible en data/chroma/ot_1844; storage aparece con directorios UUID, posible desalineaciï¿½n con ruta canï¿½nica documentada
- Propuesta: usar colecciï¿½n actual para consultas y normalizar/verificar persistencia Chroma canï¿½nica antes de prï¿½xima reindexaciï¿½n
## 2026-03-11 15:56 UTC-3
- Trigger: foco en P6-Standalone-Automation
- Archivos leÃ­dos: projects/P6-Standalone-Automation/README.md; projects/P6-Standalone-Automation/MEMORY.md; projects/P6-Standalone-Automation/LOG.md (100 lÃ­neas + continuaciÃ³n); projects/P6-Standalone-Automation/INDEX.csv (50 lÃ­neas); projects/P6-Standalone-Automation/data/ (verificado); data/chroma/* (verificado)
- RAG: sÃ­ + 400 chunks + top score 0.000 (rerank top -11.1720)
- Brechas: la colecciÃ³n `p6_standalone_automation` existe y responde, pero no aparece como carpeta nominal `data/chroma/p6_standalone_automation` porque Chroma persiste con directorios UUID; la query de estado actual devuelve chunks dÃ©biles/genÃ©ricos del PDF estÃ¡ndar, no del estado operativo vivo
- Propuesta: crear/indexar un resumen operativo propio del proyecto y usar queries temÃ¡ticas mÃ¡s especÃ­ficas (carga DB, XER vs DB, PV/EV semanal) para retrieval Ãºtil
## [2026-03-11 16:09 UTC-3] — Foco en P6-Standalone-Automation
- Trigger: "hagamos foco en el proyecto relacionado a P6, lo reconoces?"
- Archivos leídos: projects/P6-Standalone-Automation/README.md; projects/P6-Standalone-Automation/MEMORY.md; projects/P6-Standalone-Automation/LOG.md (100 líneas); projects/P6-Standalone-Automation/INDEX.csv (50 líneas); projects/P6-Standalone-Automation/data/*; data/chroma/* + verificación SQLite de colección
- RAG ejecutada: sí ? 767 chunks, top rerank=3.5299
- Brechas: verificación por carpeta `data/chroma/p6_standalone_automation` da falso negativo porque Chroma persiste por UUID + `chroma.sqlite3`; falta formalizar comparador reusable XER vs DB; falta cargador seguro reusable Excel?DB
- Propuesta: seguir sobre `projects/P6-Standalone-Automation` como proyecto P6 canónico y priorizar comparador XER vs DB o cargador seguro de avances según objetivo inmediato
## 2026-03-11 21:32 UTC-3
- Trigger: foco en P6-Standalone-Automation
- Archivos leídos:
  - projects/P6-Standalone-Automation/README.md
  - projects/P6-Standalone-Automation/MEMORY.md
  - projects/P6-Standalone-Automation/LOG.md (100 líneas)
  - projects/P6-Standalone-Automation/INDEX.csv (50 líneas)
  - projects/P6-Standalone-Automation/docs/OPERATING_SUMMARY_2026-03-11.md
- RAG: sí + 767 chunks + top score 0.593
- Brechas:
  - comparador reusable XER vs DB aún por consolidar
  - recuperación semántica del estado operativo todavía imperfecta
  - ruido alto en scripts/ por temporales
  - formalizar cargador seguro Excel -> DB como herramienta única
- Propuesta:
  - consolidar compare_xer_db_weekly.py + pv_engine.py como ruta única
  - mejorar indexación/prioridad del operating summary
